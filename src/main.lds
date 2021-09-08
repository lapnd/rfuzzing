SECTIONS
{
. = 0x10078;
.text : { *(.text) }
. = 0x3fff00;
.data : { *(.data) }
}
