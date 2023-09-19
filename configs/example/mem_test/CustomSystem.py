from m5.util import addToPath
addToPath('../')

from mem_test import CustomNetwork as cnet
# Apply extra custom options for vanilla system configuration
def customize_system(options, system) -> bool:
    cnet.customize_network(options, system.ruby.network)
    return True