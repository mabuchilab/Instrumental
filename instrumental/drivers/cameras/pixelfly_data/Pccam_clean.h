# 1 "Pccam.h"
# 1 "<command-line>"
# 1 "Pccam.h"


# 1 "pcc_struct.h" 1





typedef struct
{


  int boardnr;
  HANDLE hdriver;
  HANDLE headevent;

  int bufalloc[64];
  void *mapadr[64];
  int mapsize[64];
  int mapoffset[64];
  int mapcount[64];
  HANDLE bufevent[64];
  BOOLEAN event_internal[64];

  HINSTANCE pfcamlib;
}PCC_DEVICE_ENTRY;


typedef struct
{
 int bufnr;
 unsigned int BufferStatus;
 unsigned int counter;
 HANDLE hBufferEvent;
}PCC_Buflist;
# 4 "Pccam.h" 2





int INITBOARD(int board,HANDLE *hdriver);
# 25 "Pccam.h"
int INITBOARDP(int board,HANDLE *hdriver);



int CLOSEBOARD(HANDLE *hdriver);




int RESETBOARD(HANDLE hdriver);
# 44 "Pccam.h"
int GETBOARDPAR(HANDLE hdriver,void *buf, int len);
# 56 "Pccam.h"
int GETBOARDVAL(HANDLE hdriver,int pcc_val,void *data);
# 67 "Pccam.h"
int SETMODE(HANDLE hdriver,int mode,
                  int explevel,int exptime,
                  int hbin,int vbin,
         int gain,int offset,
         int bit_pix,int shift);
# 154 "Pccam.h"
int GETMODE(HANDLE hdriver,int *mode,
                  int *explevel,int *exptime,
                  int *hbin,int *vbin,
         int *gain,int *offset,
         int *bit_pix,int *shift);



int WRRDORION(HANDLE hdriver,int cmnd,int *data);
# 180 "Pccam.h"
int SET_EXPOSURE(HANDLE hdriver,int time);
# 189 "Pccam.h"
int TRIGGER_CAMERA(HANDLE hdriver);





int START_CAMERA(HANDLE hdriver);
int STOP_CAMERA(HANDLE hdriver);
# 208 "Pccam.h"
int GETSIZES(HANDLE hdriver,int *ccdxsize,int *ccdysize,
                   int *actualxsize,int *actualysize,
       int *bit_pix);
# 223 "Pccam.h"
int READTEMPERATURE(HANDLE hdriver,int *ccd);
# 234 "Pccam.h"
int READVERSION(HANDLE hdriver,int typ,char *vers,int len);
# 247 "Pccam.h"
int GETBUFFER_STATUS(HANDLE hdriver,int bufnr,int mode,int *stat,int len);
# 280 "Pccam.h"
int GETBUFFERVAL(HANDLE hdriver,int bufnr,int pcc_bufval,void *data);
# 293 "Pccam.h"
int ADD_BUFFER_TO_LIST(HANDLE hdriver,int bufnr,int size,int offset,int data);
# 316 "Pccam.h"
int ADD_PHYS_BUFFER_TO_LIST(HANDLE hdriver,int bufnr,int size,int num_entry,unsigned int *table);
# 341 "Pccam.h"
int REMOVE_BUFFER_FROM_LIST(HANDLE hdriver,int bufnr);
# 351 "Pccam.h"
int ALLOCATE_BUFFER(HANDLE hdriver,int *bufnr,int *size);
# 367 "Pccam.h"
int FREE_BUFFER(HANDLE hdriver,int bufnr);






int SETBUFFER_EVENT(HANDLE hdriver,int bufnr,HANDLE *hPicEvent);
# 388 "Pccam.h"
int MAP_BUFFER(HANDLE hdriver,int bufnr,int size,int offset,DWORD *linadr);
# 400 "Pccam.h"
int MAP_BUFFER_EX(HANDLE hdriver,int bufnr,int size,int offset,void** linadr);
# 412 "Pccam.h"
int UNMAP_BUFFER(HANDLE hdriver,int bufnr);
# 442 "Pccam.h"
int SETORIONINT(HANDLE hdriver,int bufnr, int mode,unsigned char *cmnd,int len);
# 455 "Pccam.h"
int GETORIONINT(HANDLE hdriver,int bufnr, int mode,unsigned char *data,int len);
# 470 "Pccam.h"
int READEEPROM(HANDLE hdriver,int mode,int adr,char *data);
# 484 "Pccam.h"
int WRITEEEPROM(HANDLE hdriver,int mode,int adr,char data);
# 496 "Pccam.h"
int SETTIMEOUTS(HANDLE hdriver,DWORD dma, DWORD proc, DWORD head);
# 505 "Pccam.h"
int SETDRIVER_EVENT(HANDLE hdriver,int mode,HANDLE *hHeadEvent);
# 525 "Pccam.h"
int READ_TEMP(HANDLE hdriver,int *ccd_temp,int *ele_temp);
# 537 "Pccam.h"
int SET_NOMINAL_PELTIER_TEMP(HANDLE hdriver,int temp);

int GET_NOMINAL_PELTIER_TEMP(HANDLE hdriver,int *temp);
# 555 "Pccam.h"
int SET_STANDBY_MODE(HANDLE hdriver,int mode);
# 565 "Pccam.h"
int GET_STANDBY_MODE(HANDLE hdriver,int *mode);
# 579 "Pccam.h"
int PCC_MEMCPY(void *dest,void *source,int len);
# 591 "Pccam.h"
int PCC_GET_VERSION(HANDLE hdriver, char *dll,char *sys);
# 604 "Pccam.h"
int PCC_WAITFORBUFFER(HANDLE hdriver, int nr_of_buffer, PCC_Buflist *bl, int timeout);
int PCC_RESETEVENT(HANDLE hdriver,int bufnr);
