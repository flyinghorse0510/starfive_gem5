/*======================================================================*/
/* Proxy kernel linker script                                           */
/*======================================================================*/
/* This is the linker script used when building the proxy kernel. */

/*----------------------------------------------------------------------*/
/* Setup                                                                */
/*----------------------------------------------------------------------*/

/* The OUTPUT_ARCH command specifies the machine architecture where the
   argument is one of the names used in the BFD library. More
   specifically one of the entires in bfd/cpu-mips.c */

OUTPUT_ARCH( "riscv" )
ENTRY(_start)

/*----------------------------------------------------------------------*/
/* Sections                                                             */
/*----------------------------------------------------------------------*/

SECTIONS
{

  /* text: test code section */
  . = 0x80000000;
  .text.init : { *(.text.init) }

  . = ALIGN(0x1000);
  .tohost : { *(.tohost) }

  .text : { *(.text) }

  /* data segment */
  .data : { *(.data) }

  .sdata : {
    __global_pointer$ = . + 0x800;
    *(.srodata.cst16) *(.srodata.cst8) *(.srodata.cst4) *(.srodata.cst2) *(.srodata*)
    *(.sdata .sdata.* .gnu.linkonce.s.*)
  }

  /* bss segment */
  .sbss : {
    *(.sbss .sbss.* .gnu.linkonce.sb.*)
    *(.scommon)
  }
  .bss : { *(.bss) }

  /* thread-local data segment */
  .tdata :
  {
    _tdata_begin = .;
    _tls_data = .;
    *(.tdata.begin)
    *(.tdata)
    *(.tdata.end)
    _tdata_end = .;
  }
  .tbss :
  {
    *(.tbss)
    *(.tbss.end)
    _tbss_end = .;
  }
  .stack :
  {
    . = ALIGN(0x1000);

    PROVIDE (_stack_start = .);
    /*16MB*/
    . += 0x1000000;
    . = ALIGN(0x8);
    PROVIDE (_stack_end = .);
  }


  .heap :
  {
    . = ALIGN(0x1000);

    PROVIDE (_heap_start = .);
    /*16MB*/
    . += 0x1000000;
    . = ALIGN(8);
    PROVIDE (_heap_end = .);
  }


  /* End of uninitalized data segement */
  _end = .;
}

