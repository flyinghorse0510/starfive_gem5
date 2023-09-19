

def customize_simple_link(options, simpleLink) -> bool:
    for i in range(len(simpleLink)):
        simpleLink[i].bandwidth_factor = options.simple_bandwidth_factor
    return True