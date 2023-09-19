from m5.util import addToPath
addToPath('../')

from mem_test import CustomLink as clink


# Apply extra custom options for vanilla network configuration
def customize_network(options, simpleNetwork) -> bool:
    clink.customize_simple_link(options, simpleNetwork.int_links)
    clink.customize_simple_link(options, simpleNetwork.ext_links)
    return True
    