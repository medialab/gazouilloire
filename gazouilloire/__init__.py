import json
import os

try:
    with open(os.path.realpath(os.path.join(__file__, "..", "..", "config.json")), "r") as confile:
        conf = json.loads(confile.read())
        analyzer = conf.get('text_analyzer', 'standard')
except Exception as e:
    print('WARNING - Could not open config.json: %s %s' % (type(e), e))
    analyzer = 'standard'

