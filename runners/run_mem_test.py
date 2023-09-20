import build_tool as buildTool
import util
import argparse, os, sys

def customize_runner(memTestParser) -> bool:
    memTestParser.add_argument("--test_file_dir", type=str, default="")
    memTestParser.add_argument("--test_file", type=str, default="mem_test_data.bin")
    memTestParser.add_argument("--num_cpus", type=int, default=1)
    memTestParser.add_argument("--num_dmas", type=int, default=0)
    memTestParser.add_argument("--working_set", type=int, default=1024)
    memTestParser.add_argument("--maxloads", type=int, default=1000)
    memTestParser.add_argument("--debug_flags", nargs="*", default=["SeqMemLatTest", "DirectedMemTest"])
    memTestParser.set_defaults(addr_intrlvd_or_tiled=False)
    memTestParser.set_defaults(randomize_acc=False)
    return True

if __name__ == "__main__":
    
    rootRepoPath = util.get_repo_root()
    if rootRepoPath is None:
        raise Exception("Git repo not found!")
    
    sys.path.insert(0, "%s/runners/mem_test" %(rootRepoPath))
    from mem_test import MemTestGenerator as dataGenerator
    from mem_test import MemTestTranslator as dataTranslator
    
    parser = argparse.ArgumentParser(
                    prog='StarFive Test Runners (MemTest)',
                    description='StarFive MemTest')
    # Subcommand Parser
    subcmdParser = parser.add_subparsers(dest='subcmd', required=True)
    buildParser = subcmdParser.add_parser("build", help="Build gem-5 simulator")
    memTestParser = subcmdParser.add_parser("test", help="Perform gem-5 memory test")
    dataGenParser = subcmdParser.add_parser("generate", help="Generate gem-5 memory test data")
    dataTransParser = subcmdParser.add_parser("translate", help="Translate gem-5 memory test data into readable format")
    ## Build subcommand parser
    buildTool.customize_build(buildParser)
    dataGenerator.customize_generator(dataGenParser)
    dataTranslator.customize_translator(dataTransParser)
    customize_runner(memTestParser)
    
    # Parse commands
    options = parser.parse_args()
    # Assign root repo path
    options.rootRepoPath = rootRepoPath
    # Invoke subcommands
    if options.subcmd == "build":
        # Build simulators
        buildTool.build(options)
        
    elif options.subcmd == "test":
        # Invoke memTest
        # Construct memory test file path
        if options.test_file_dir is None or options.test_file_dir == "":
            options.test_file_dir = "%s/runners/mem_test/data" %(options.rootRepoPath)
        options.mem_test_file_path = "%s/%s" %(options.test_file_dir, options.test_file)
        
        # Construct debug flags
        options.allDebugFlags = ""
        if (len(options.debug_flags) > 0):
            for i in range(len(options.debug_flags)):
                options.allDebugFlags += options.debug_flags[i] + ","
            options.allDebugFlags = "--debug-flags=" + options.allDebugFlags[:-1]
        
        util.exec_shell_cmd(
            "pushd %s && "
            "build/RISCV_CHI/gem5.opt "
            "%s "
            "configs/example/seq_ruby_mem_test.py "
            "--mem-test-type=directed_test "
            "--ruby "
            "--cacheline_size=64 "
            "--num-dirs=1 "
            "--num-l3caches=1 "
            "--mem-size='4GB' "
            "--progress=1000000 "
            "--num-cpus=%d "
            "--num-dmas=%d "
            "--size-ws=%d "
            "--maxloads=%d "
            "--mem_test_file_path=%s && "
            "popd"
            %(
                options.rootRepoPath,
                options.allDebugFlags,
                options.num_cpus,
                options.num_dmas,
                options.working_set,
                options.maxloads,
                options.mem_test_file_path
            ),
            directStdout = True, 
            directStderr = True
        )
        
    elif options.subcmd == "generate":
        # Create directory
        if options.output_path is None or options.output_path == "":
            options.output_path = "%s/runners/mem_test/data" %(options.rootRepoPath)
        
        options.path = "%s/%s" %(options.output_path, options.output_file)
        util.create_dir(options.output_path)
        
        # Generate data
        dataGenerator.generate(options)
        
    elif options.subcmd == "translate":
        # Translate data
        dataTranslator.translate_binary("%s/runners/mem_test/data/mem_test_data.bin" %(options.rootRepoPath), "%s/runners/mem_test/data/mem_test_data.txt" %(options.rootRepoPath))
        
        
