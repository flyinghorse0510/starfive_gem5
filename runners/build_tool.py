import util, sys, os
import argparse
# Build MemTest Runner
def build_mem_test_runner(options) -> bool:
    # Delete stale build files
    util.exec_shell_cmd("pushd %s/runners/mem_test && rm -rf build && mkdir -p build && popd" %(options.rootRepoPath), directStdout = True, directStderr = True)
    # Build generator
    util.exec_shell_cmd("pushd %s/runners/mem_test && g++ -O3 -Wall -shared -std=c++11 -fPIC $(python3 -m pybind11 --includes) mem_test_generator.cc -o build/mem_test_generator$(python3-config --extension-suffix) && popd" %(options.rootRepoPath), directStdout = True, directStderr = True)
    # Build translator
    util.exec_shell_cmd("pushd %s/runners/mem_test && g++ -O3 -Wall -shared -std=c++11 -fPIC $(python3 -m pybind11 --includes) mem_test_translator.cc -o build/mem_test_translator$(python3-config --extension-suffix) && popd" %(options.rootRepoPath), directStdout = True, directStderr = True)
    return True

# Build Simulator
def build_simulator(options) -> bool:
    totalBuildTasks = len(options.ISA) * len(options.protocol)
    print("Building Simulators... (%d tasks in total)" %(totalBuildTasks))
    for i in range(len(options.ISA)):
        ISA = options.ISA[i]
        for j in range(len(options.protocol)):
            protocol = options.protocol[j]
            print("Building simulator: ISA->%s, Protocol->%s ===> build/%s_%s/gem5.opt" %(ISA, protocol, ISA, protocol))
            util.exec_shell_cmd("pushd %s && scons build/%s_%s/gem5.opt --default=%s PROTOCOL=%s SLICC_HTML=False && popd" %(options.rootRepoPath, ISA, protocol, ISA, protocol), directStdout = True, directStderr = True)
    return True

buildCmdDict = {
    "simulator": build_simulator,
    "mem_test_runner": build_mem_test_runner
}

def build(options) -> bool:
    buildTargetsList = options.target
    if options.build_mem_only:
        buildTargetsList = ["mem_test_runner"]
    
    for i in range(len(buildTargetsList)):
        print("Building %s..." %(buildTargetsList[i]))
        buildCmdDict[buildTargetsList[i]](options)
        print("Finish buding %s" %(buildTargetsList[i]))
    return True

# Build subcommand parser
def customize_build(buildParser) -> bool:
    buildParser.add_argument("-i", "-I", "--ISA", "--arch", "--isa", dest="ISA", nargs="+", default=["RISCV"])
    buildParser.add_argument("-p", "-P", "--protocol", "--Protocol", "--PROTOCOL", dest="protocol", nargs="+", default=["CHI"])
    buildParser.add_argument("-j", "-J", "--job", dest="job", type=int, default=16)
    buildParser.add_argument("-t", "-T", "--target", dest="target", nargs="+", default=["simulator", "mem_test_runner"])
    buildParser.add_argument("--build_mem_only", dest="build_mem_only", action='store_true')
    buildParser.set_defaults(build_mem_only=False)
    return True