PCC_BUF_STAT_WRITE = lambda ptr: ((ptr+0)[0] & 0x01)
PCC_BUF_STAT_WRITE_DONE = lambda ptr: (((ptr+0)[0] >> 1) & 0x01)
PCC_BUF_STAT_QUEUED = lambda ptr: (((ptr+0)[0] >> 2) & 0x01)
PCC_BUF_STAT_CANCELLED = lambda ptr: (((ptr+0)[0] >> 3) & 0x01)

PCC_BUF_STAT_SELECT = lambda ptr: (((ptr+0)[0] >> 4) & 0x01)
PCC_BUF_STAT_SELECT_DONE = lambda ptr: (((ptr+0)[0] >> 5) & 0x01)
PCC_BUF_STAT_MAPPED = lambda ptr: (((ptr+0)[0] >> 6) & 0x01)
PCC_BUF_STAT_I4BYTES = lambda ptr: (((ptr+0)[0] >> 7) & 0x01)

PCC_BUF_STAT_REMOVED = lambda ptr: (((ptr+0)[0] >> 8) & 0x01)
PCC_BUF_STAT_TRANS_BYTE = lambda ptr: (((ptr+0)[0] >> 9) & 0x01)

PCC_BUF_STAT_ERROR = lambda ptr: (((ptr+0)[0] >> 12) & 0x0F)
PCC_BUF_STAT_BURST_ERROR = lambda ptr: (((ptr+0)[0] >> 12) & 0x01)
PCC_BUF_STAT_SIZE_ERROR = lambda ptr: (((ptr+0)[0] >> 13) & 0x01)
PCC_BUF_STAT_PCI_ERROR = lambda ptr: (((ptr+0)[0] >> 14) & 0x01)
PCC_BUF_STAT_TIMEOUT_ERROR = lambda ptr: (((ptr+0)[0] >> 15) & 0x01)

PCC_BUF_OPENCOUNT = lambda ptr: (((ptr+0)[0] >> 16) & 0xFF)
PCC_BUF_MAPCOUNT = lambda ptr: ((ptr+14)[0] >> 16)

PCC_BUF_EXPTIME = lambda ptr: (ptr+1)[0]

PCC_BUF_ACT_OFFSET = lambda ptr: (ptr+17)[0]
PCC_BUF_ACT_SIZE = lambda ptr: (ptr+18)[0]
PCC_BUF_ACT_TRANSFER = lambda ptr: (ptr+19)[0]

PCC_BUF_TOTAL_SIZE = lambda ptr: ((ptr+21)[0] * (ptr+22)[0])

#define PCC_BOARDTYP(ptr) (*((dword *)ptr+0)&0x0FF0)
#define PCC_BOARDNR(ptr)  (*((dword *)ptr+0)&0x0F)
#define PCC_BOARDINIT(ptr)    ((*((dword *)ptr+0)&0x10000000) ? 1 : 0)

#define PCC_BOARD_420L(ptr)   ((*((dword *)ptr+0)&0x00001000) ? 1 : 0)
#define PCC_BOARD_SVGA(ptr)   ((*((dword *)ptr+0)&0x00002000) ? 1 : 0)
#define PCC_BOARD_HVGA(ptr)   ((*((dword *)ptr+0)&0x00004000) ? 1 : 0)
#define PCC_BOARD_IR(ptr)     ((*((dword *)ptr+0)&0x00008000) ? 1 : 0)
#define PCC_BOARD_DOUBLE(ptr) ((*((dword *)ptr+0)&0x00010000) ? 1 : 0)
#define PCC_BOARD_EXP(ptr)    ((*((dword *)ptr+0)&0x00020000) ? 1 : 0)
#define PCC_BOARD_VGA2(ptr)   ((*((dword *)ptr+0)&0x00040000) ? 1 : 0)
#define PCC_BOARD_QE(ptr)     ((*((dword *)ptr+0)&0x00080000) ? 1 : 0)
#define PCC_BOARD_SMALL(ptr)  ((*((dword *)ptr+0)&0x00100000) ? 1 : 0)
#define PCC_BOARD_5US(ptr)    ((*((dword *)ptr+0)&0x00200000) ? 1 : 0)
#define PCC_BOARD_F32(ptr)    ((*((dword *)ptr+0)&0x00400000) ? 1 : 0)

#define PCC_CAMSTAT(ptr)  (*((dword *)ptr+1))
#define PCC_CAM_RUN(ptr)  (*((dword *)ptr+1)&0x01)
#define PCC_NO_HEAD(ptr) ((*((dword *)ptr+1)>>27)&0x01)

#define PCC_CCDXSIZE(ptr)  *((dword *)ptr+2)
#define PCC_CCDYSIZE(ptr)  *((dword *)ptr+3)

#define PCC_MODE(ptr)      *((dword *)ptr+4)
#define PCC_EXPTIME(ptr)   *((dword *)ptr+5)
#define PCC_EXPLEVEL(ptr)  *((dword *)ptr+6)
#define PCC_HBIN(ptr)    ((*((dword *)ptr+7)>>7)&0x01)
#define PCC_VBIN(ptr)     (*((dword *)ptr+7)&0x0F) //@ver1.012 back to 0x0f
#define PCC_REGW(ptr)    ((*((dword *)ptr+7)>>4)&0x01)
#define PCC_GAIN(ptr)      *((dword *)ptr+8)
#define PCC_BITPIX(ptr)  ((*((dword *)ptr+9)==0) ? 12 : 8)
#define PCC_SHIFT(ptr)   ((*((dword *)ptr+9)==0) ? 0  : (*((dword *)ptr+9)-1))
#define PCC_OFFSET(ptr)    *((dword *)ptr+10)

#define PCC_LASTEXP(ptr)   *((dword *)ptr+11)

#define PCC_CCDTYPE(ptr)   *((dword *)ptr+17)
#define PCC_LINETIME(ptr)   *((dword *)ptr+18)

#define PCC_DOUBLE(ptr)   (*((dword *)ptr+12)&0x01)
#define PCC_PRISMA(ptr)  ((*((dword *)ptr+12)>>8)&0x0FF)
#define PCC_COLOR(ptr)    (*((dword *)ptr+17)&0x01)  //@ver1.008

#define PCC_CCDVGA(ptr)  (((*((dword *)ptr+17)&~0x0F)==0x00) ? 1 : 0)
#define PCC_CCDSVGA(ptr) (((*((dword *)ptr+17)&~0x0F)==0x10) ? 1 : 0)
#define PCC_CCDHVGA(ptr) (((*((dword *)ptr+17)&~0x0F)==0x20) ? 1 : 0)
#define PCC_CCDIR(ptr)   (((*((dword *)ptr+17)&~0x0F)==0x30) ? 1 : 0)

#define PCC_DEVOPENCOUNT(ptr) *((dword *)ptr+20)
#define PCC_ACTBUFFERIN(ptr)  ((*((dword *)ptr+13)==0) ? FALSE : TRUE)
#define PCC_NEXTBUFFERIN(ptr) ((*((dword *)ptr+14)==*((dword *)ptr+15)) ? FALSE : TRUE)
