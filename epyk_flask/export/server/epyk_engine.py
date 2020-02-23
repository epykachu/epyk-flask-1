import yaml, hashlib, sys, os, importlib
config = None
engine_app = None

class MissingEpykFlaskConfigException(Exception):
  """Exception to be raised when the configuration is missing"""
  pass

class MissingAttrConfig(Exception):
  """Exception to be raised when an attribute is missing from the configuration"""
  pass

class MissingRptObjException(Exception):
  """Exception to be raised when the REPORT_OBJECT attribute is missing from a script to be run"""
  pass

def init(config_path=None):
  global config
  global engine_app
  if config_path is None:
    with open('config.yaml', 'r') as f:
      config = yaml.load(f, Loader=yaml.FullLoader)
  else:
    with open(config_path, 'r') as f:
      config = yaml.load(f, Loader=yaml.FullLoader)

  engine_app = importlib.import_module(config['server_interface'])
  for repo in config['repos']:
    sys.path.append(repo['path'])
  for path in config['endpoints']['path']:
    sys.path.append(path)

def hash_content(file_path):
  with open(file_path, 'rb') as f:
    f_hash = hashlib.blake2b()
    while True:
      data = f.read(8192)
      if not data:
        break

      f_hash.update(data)
  return f_hash.hexdigest()

def parse_config(attr, config):
  """"""
  attr_len = len(attr)
  if attr_len != 0:
    if attr[0] not in config:
      raise MissingAttrConfig('Missing attribute %s from configuration' % attr)

    if attr_len > 1:
      parse_config(attr[1], config[attr[0]])


def config_required(*dec_args):
  """Allows to check specific properties have been set before using a function"""
  def wrap(func):
    if config is None:
      raise MissingEpykFlaskConfigException('Configuration required for endpoint: %s. Set epyk_config from %s' % (func.__name__, __name__))

    for attr in dec_args:
      parse_config(attr, config)

    def inner(*args, **kwargs):
      return func(*args, **kwargs)

    return inner

  return wrap

def run_script(folder_name, script_name):
  """
  """
  print(script_name)
  if not script_name.endswith('.py'):
    full_name = '%s.py' % script_name
  else:
    full_name = script_name
    script_name = script_name.replace('.py', '')
  print(sys.path)
  mod = importlib.import_module('%s.%s' % (folder_name, script_name))
  rptObj = getattr(mod, 'REPORT_OBJECT', False)
  if not rptObj:
    MissingRptObjException('Your report: %s is missing the REPORT_OBJECT attribute which should be an Report Object from %s' % (mod.__name__, Report.__module__))
  if hasattr(mod, 'FAVICON'):
    rptObj.logo = mod.FAVICON
  if getattr(mod, 'CONTROLLED_ACCESS', False):
    controlLevel = getattr(mod, 'CONTROLLED_LEVEL', 'ENV').upper()

  script_hash = hash_content(os.path.join(os.path.abspath(os.path.dirname(mod.__name__)), full_name))
  output_name = '%s_%s_%s' % (folder_name, script_name, script_hash)
  rptObj.outs.html_file(path=config['html_output'], name=output_name)
  return os.path.join(config['html_output'], 'html', output_name)


def register(*args):
  return engine_app.engine_register(*args)


def linked_script(folder_name='root', script_name='index'):
  """"""
  def wrap(func):

    def inner(*args, **kwargs):
      script_hash = ''
      file_path = os.path.join(config['main_repo']['path'], folder_name, script_name)
      if os.path.exists(file_path):
        script_hash = hash_content(file_path)
      else:
        for repo in config['repos']:
          file_path = os.path.join(repo['path'], folder_name, script_name)
          if os.path.exists(file_path):
            script_hash = hash_content(file_path)
            break

      output_file = os.path.join(config['html_output'], '%s_%s_%s.html' % (folder_name, script_name, script_hash))
      if os.path.exists(output_file):
        with open(output_file, 'r') as f:
          data = f.read()
        return data

      return func(*args, **kwargs)

    return inner

  return wrap
