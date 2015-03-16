// Header file combined from master.h and pvcam.h

// Has been run through C preprocessor on a 32-bit WinXP system to clean it of
// macros. Basically, we need this for typedefs, enums, and function
// declarations.
# 1 "pvcam.h"
# 1 "<command-line>"
# 1 "./master.h" 1
# 73 "./master.h"
enum { PV_FAIL, PV_OK };

typedef unsigned short rs_bool, * rs_bool_ptr;
typedef char * char_ptr;
typedef signed char int8, * int8_ptr;
typedef unsigned char uns8, * uns8_ptr;
typedef short int16, * int16_ptr;
typedef unsigned short uns16, * uns16_ptr;
typedef long int32, * int32_ptr;
typedef unsigned long uns32, * uns32_ptr;
typedef double flt64, * flt64_ptr;
typedef void * void_ptr;
typedef void_ptr * void_ptr_ptr;

typedef const rs_bool * rs_bool_const_ptr;
typedef const char * char_const_ptr;
typedef const int8 * int8_const_ptr;
typedef const uns8 * uns8_const_ptr;
typedef const int16 * int16_const_ptr;
typedef const uns16 * uns16_const_ptr;
typedef const int32 * int32_const_ptr;
typedef const uns32 * uns32_const_ptr;
typedef const flt64 * flt64_const_ptr;



  typedef unsigned short boolean;

typedef boolean * boolean_ptr;
typedef const boolean * boolean_const_ptr;
# 1 "<command-line>" 2
# 1 "pvcam.h"






static const char *_pvcam_h_="$Header: /PVCAM v2.6/SourceCommon/pvcam.h 29    11/07/03 12:14p Ghavenga $";
# 239 "pvcam.h"
enum
{ OPEN_EXCLUSIVE };
# 250 "pvcam.h"
enum
{ NORMAL_COOL, CRYO_COOL };
# 260 "pvcam.h"
enum
{ MPP_UNKNOWN, MPP_ALWAYS_OFF, MPP_ALWAYS_ON, MPP_SELECTABLE };





enum
{ SHTR_FAULT, SHTR_OPENING, SHTR_OPEN, SHTR_CLOSING, SHTR_CLOSED,
  SHTR_UNKNOWN
};



enum
{ PMODE_NORMAL, PMODE_FT, PMODE_MPP, PMODE_FT_MPP,
  PMODE_ALT_NORMAL, PMODE_ALT_FT, PMODE_ALT_MPP, PMODE_ALT_FT_MPP,
  PMODE_INTERLINE
};



enum
{ COLOR_NONE, COLOR_RGGB = 2 };





enum
{ ATTR_CURRENT, ATTR_COUNT, ATTR_TYPE, ATTR_MIN, ATTR_MAX, ATTR_DEFAULT,
  ATTR_INCREMENT, ATTR_ACCESS, ATTR_AVAIL
};





enum
{ ACC_ERROR, ACC_READ_ONLY, ACC_READ_WRITE, ACC_EXIST_CHECK_ONLY,
  ACC_WRITE_ONLY
};




enum
{ IO_TYPE_TTL, IO_TYPE_DAC };



enum
{ IO_DIR_INPUT, IO_DIR_OUTPUT, IO_DIR_INPUT_OUTPUT };


enum
{ IO_ATTR_DIR_FIXED, IO_ATTR_DIR_VARIABLE_ALWAYS_READ };



enum
{ EDGE_TRIG_POS = 2, EDGE_TRIG_NEG };



enum
{ OUTPUT_NOT_SCAN = 0, OUTPUT_SHUTTER, OUTPUT_NOT_RDY, OUTPUT_LOGIC0,
  OUTPUT_CLEARING, OUTPUT_NOT_FT_IMAGE_SHIFT, OUTPUT_RESERVED,
  OUTPUT_LOGIC1
};



enum
{ INTENSIFIER_SAFE = 0, INTENSIFIER_GATING, INTENSIFIER_SHUTTER };



enum
{ READOUT_PORT_MULT_GAIN = 0,
  READOUT_PORT_NORMAL,
  READOUT_PORT_LOW_NOISE,
  READOUT_PORT_HIGH_CAP,

  READOUT_PORT1 = 0,
  READOUT_PORT2 = 1
};



enum
{ ANTIBLOOM_NOTUSED = 0, ANTIBLOOM_INACTIVE, ANTIBLOOM_ACTIVE };



enum
{ CLEAR_NEVER, CLEAR_PRE_EXPOSURE, CLEAR_PRE_SEQUENCE, CLEAR_POST_SEQUENCE,
  CLEAR_PRE_POST_SEQUENCE, CLEAR_PRE_EXPOSURE_POST_SEQ, MAX_CLEAR_MODE
};
# 370 "pvcam.h"
enum
{ OPEN_NEVER, OPEN_PRE_EXPOSURE, OPEN_PRE_SEQUENCE, OPEN_PRE_TRIGGER,
  OPEN_NO_CHANGE
};
# 393 "pvcam.h"
enum
{ TIMED_MODE, STROBED_MODE, BULB_MODE, TRIGGER_FIRST_MODE, FLASH_MODE,
  VARIABLE_TIMED_MODE, INT_STROBE_MODE, MAX_EXPOSE_MODE
};




typedef enum _PP_FEATURE_IDS {
   PP_FEATURE_RING_FUNCTION,
   PP_FEATURE_BIAS,
   PP_FEATURE_BERT,
   PP_FEATURE_QUANT_VIEW,
   PP_FEATURE_BLACK_LOCK,
   PP_FEATURE_TOP_LOCK,
   PP_FEATURE_VARI_BIT,
   PP_FEATURE_FLUX_VIEW,
   PP_FEATURE_MAX
} PP_FEATURE_IDS, *PPP_FEATURE_IDS;






typedef enum _PP_PARAMETER_IDS {
   PP_PARAMETER_RF_FUNCTION = (0),
   PP_FEATURE_BIAS_ENABLED = (10),
   PP_FEATURE_BIAS_LEVEL,
   PP_FEATURE_BERT_ENABLED = (20),
   PP_FEATURE_BERT_THRESHOLD,
   PP_FEATURE_QUANT_VIEW_ENABLED = (30),
   PP_FEATURE_QUANT_VIEW_E,
   PP_FEATURE_BLACK_LOCK_ENABLED = (40),
   PP_FEATURE_BLACK_LOCK_BLACK_CLIP,
   PP_FEATURE_TOP_LOCK_ENABLED = (50),
   PP_FEATURE_TOP_LOCK_WHITE_CLIP,
   PP_FEATURE_VARI_BIT_ENABLED = (60),
   PP_FEATURE_VARI_BIT_BIT_DEPTH,
   PP_FEATURE_FLUX_VIEW_ENABLED = (70),
   PP_FEATURE_FLUX_VIEW_TIME_SCALE,
   PP_PARAMETER_ID_MAX
} PP_PARAMETER_IDS, *PPP_PARAMETER_IDS;
# 449 "pvcam.h"
enum
{
  READOUT_NOT_ACTIVE,
  EXPOSURE_IN_PROGRESS,
  READOUT_IN_PROGRESS,
  READOUT_COMPLETE,
  FRAME_AVAILABLE = READOUT_COMPLETE,
  READOUT_FAILED,
  ACQUISITION_IN_PROGRESS,
  MAX_CAMERA_STATUS
};






enum
{ CCS_NO_CHANGE, CCS_HALT, CCS_HALT_CLOSE_SHTR, CCS_CLEAR,
  CCS_CLEAR_CLOSE_SHTR, CCS_OPEN_SHTR, CCS_CLEAR_OPEN_SHTR
};


enum
{ EVENT_START_READOUT, EVENT_END_READOUT };



enum
{ NO_FRAME_IRQS, BEGIN_FRAME_IRQS, END_FRAME_IRQS, BEGIN_END_FRAME_IRQS };





enum
{ CIRC_NONE, CIRC_OVERWRITE, CIRC_NO_OVERWRITE };



enum
{ EXP_RES_ONE_MILLISEC, EXP_RES_ONE_MICROSEC, EXP_RES_ONE_SEC };


enum
{ SCR_PRE_OPEN_SHTR, SCR_POST_OPEN_SHTR, SCR_PRE_FLASH, SCR_POST_FLASH,
  SCR_PRE_INTEGRATE, SCR_POST_INTEGRATE, SCR_PRE_READOUT, SCR_POST_READOUT,
  SCR_PRE_CLOSE_SHTR, SCR_POST_CLOSE_SHTR
};



typedef enum _PL_CALLBACK_EVENT {
 PL_CALLBACK_BOF,
 PL_CALLBACK_EOF,
 PL_CALLBACK_CHECK_CAMS,
 PL_CALLBACK_CAM_REMOVED,
 PL_CALLBACK_CAM_RESUMED,
 PL_CALLBACK_MAX
} PL_CALLBACK_EVENT, *PPL_CALLBACK_EVENT;


typedef struct
{
  uns16 s1;
  uns16 s2;
  uns16 sbin;
  uns16 p1;
  uns16 p2;
  uns16 pbin;
}
rgn_type, * rgn_ptr;
typedef const rgn_type * rgn_const_ptr;


enum
{ PRECISION_INT8, PRECISION_UNS8, PRECISION_INT16, PRECISION_UNS16,
  PRECISION_INT32, PRECISION_UNS32
};


typedef struct
{
  rs_bool rotate;
  rs_bool x_flip;
  rs_bool y_flip;
  int16 precision;
  int16 windowing;
  int32 max_inten;
  int32 min_inten;
  int16 output_x_size;
  int16 output_y_size;
}
export_ctrl_type, * export_ctrl_ptr;
typedef const export_ctrl_type * export_ctrl_const_ptr;




enum TIME_UNITS
{
  TU_DAY = 10,
  TU_HOUR = 5,
  TU_MINUTE = 4,
  TU_SEC = 3,
  TU_MSEC = 2,
  TU_USEC = 1,
  TU_NSEC = 7,
  TU_PSEC = 8,
  TU_FSEC = 9
};
# 595 "pvcam.h"
  rs_bool pl_pvcam_get_ver (uns16_ptr pvcam_version);
  rs_bool pl_pvcam_init (void);
  rs_bool pl_pvcam_uninit (void);
# 607 "pvcam.h"
  rs_bool pl_cam_check (int16 hcam);
  rs_bool pl_cam_close (int16 hcam);
  rs_bool pl_cam_get_diags (int16 hcam);
  rs_bool pl_cam_get_name (int16 cam_num, char_ptr camera_name);
  rs_bool pl_cam_get_total (int16_ptr totl_cams);
  rs_bool pl_cam_open (char_ptr camera_name, int16_ptr hcam,
                               int16 o_mode);

  rs_bool pl_cam_register_callback (int16 hcam, PL_CALLBACK_EVENT CallbackEvent, void *Callback);
  rs_bool pl_cam_deregister_callback (int16 hcam, PL_CALLBACK_EVENT CallbackEvent);
# 626 "pvcam.h"
  rs_bool pl_ddi_get_ver (uns16_ptr ddi_version);
# 644 "pvcam.h"
  int16 pl_error_code (void);
  rs_bool pl_error_message (int16 err_code, char_ptr msg);
# 667 "pvcam.h"
  rs_bool pl_get_param (int16 hcam, uns32 param_id,
                                int16 param_attribute, void_ptr param_value);
  rs_bool pl_set_param (int16 hcam, uns32 param_id,
                                void_ptr param_value);
  rs_bool pl_get_enum_param (int16 hcam, uns32 param_id, uns32 index,
                                     int32_ptr value, char_ptr desc,
                                     uns32 length);
  rs_bool pl_enum_str_length (int16 hcam, uns32 param_id, uns32 index,
                                      uns32_ptr length);
  rs_bool pl_pp_reset (int16 hcam);
# 719 "pvcam.h"
  rs_bool pl_exp_init_seq (void);
  rs_bool pl_exp_uninit_seq (void);
  rs_bool pl_exp_get_driver_buffer (int16 hcam,
                                            void_ptr_ptr pixel_stream,
                                            uns32_ptr byte_cnt);
  rs_bool pl_exp_setup_seq (int16 hcam, uns16 exp_total,
                                    uns16 rgn_total, rgn_const_ptr rgn_array,
                                    int16 exp_mode, uns32 exposure_time,
                                    uns32_ptr exp_bytes);
  rs_bool pl_exp_start_seq (int16 hcam, void_ptr pixel_stream);
  rs_bool pl_exp_setup_cont (int16 hcam, uns16 rgn_total,
                                     rgn_const_ptr rgn_array, int16 exp_mode,
                                     uns32 exposure_time, uns32_ptr exp_bytes,
                                     int16 buffer_mode);
  rs_bool pl_exp_start_cont (int16 hcam, void_ptr pixel_stream,
                                     uns32 size);
  rs_bool pl_exp_check_status (int16 hcam, int16_ptr status,
                                       uns32_ptr bytes_arrived);
  rs_bool pl_exp_check_cont_status (int16 hcam, int16_ptr status,
                                            uns32_ptr bytes_arrived,
                                            uns32_ptr buffer_cnt);
  rs_bool pl_exp_get_latest_frame (int16 hcam, void_ptr_ptr frame);
  rs_bool pl_exp_get_oldest_frame (int16 hcam, void_ptr_ptr frame);
  rs_bool pl_exp_unlock_oldest_frame (int16 hcam);
  rs_bool pl_exp_stop_cont (int16 hcam, int16 cam_state);
  rs_bool pl_exp_abort (int16 hcam, int16 cam_state);
  rs_bool pl_exp_finish_seq (int16 hcam, void_ptr pixel_stream,
                                     int16 hbuf);
  rs_bool pl_exp_unravel (int16 hcam, uns16 exposure,
                                  void_ptr pixel_stream, uns16 rgn_total,
                                  rgn_const_ptr rgn_array,
                                  uns16_ptr * array_list);
  rs_bool pl_exp_wait_start_xfer (int16 hcam, uns32 tlimit);
  rs_bool pl_exp_wait_end_xfer (int16 hcam, uns32 tlimit);







  rs_bool pl_io_script_control (int16 hcam, uns16 addr, flt64 state,
                                        uns32 location);
  rs_bool pl_io_clear_script_control (int16 hcam);
# 796 "pvcam.h"
  rs_bool pl_buf_init (void);
  rs_bool pl_buf_uninit (void);

  rs_bool pl_buf_alloc (int16_ptr hbuf, int16 exp_total,
                                int16 bit_depth, int16 rgn_total,
                                rgn_const_ptr rgn_array);
  rs_bool pl_buf_get_bits (int16 hbuf, int16_ptr bit_depth);
  rs_bool pl_buf_get_exp_date (int16 hbuf, int16 exp_num,
                                       int16_ptr year, uns8_ptr month,
                                       uns8_ptr day, uns8_ptr hour,
                                       uns8_ptr min, uns8_ptr sec,
                                       uns16_ptr msec);
  rs_bool pl_buf_set_exp_date (int16 hbuf, int16 exp_num, int16 year,
                                       uns8 month, uns8 day, uns8 hour,
                                       uns8 min, uns8 sec, uns16 msec);
  rs_bool pl_buf_get_exp_time (int16 hbuf, int16 exp_num,
                                       uns32_ptr exp_msec);
  rs_bool pl_buf_get_exp_total (int16 hbuf, int16_ptr total_exps);
  rs_bool pl_buf_get_img_bin (int16 himg, int16_ptr ibin,
                                      int16_ptr jbin);
  rs_bool pl_buf_get_img_handle (int16 hbuf, int16 exp_num,
                                         int16 img_num, int16_ptr himg);
  rs_bool pl_buf_get_img_ofs (int16 himg, int16_ptr s_ofs,
                                      int16_ptr p_ofs);
  rs_bool pl_buf_get_img_ptr (int16 himg, void_ptr_ptr img_addr);
  rs_bool pl_buf_get_img_size (int16 himg, int16_ptr x_size,
                                       int16_ptr y_size);
  rs_bool pl_buf_get_img_total (int16 hbuf, int16_ptr totl_imgs);
  rs_bool pl_buf_get_size (int16 hbuf, int32_ptr buf_size);
  rs_bool pl_buf_free (int16 hbuf);







  rs_bool pl_dd_get_info (int16 hcam, int16 bytes, char_ptr text);

  rs_bool pl_dd_get_info_length (int16 hcam, int16_ptr bytes);

  rs_bool pl_dd_get_ver (int16 hcam, uns16_ptr dd_version);

  rs_bool pl_dd_get_retries (int16 hcam, uns16_ptr max_retries);
  rs_bool pl_dd_set_retries (int16 hcam, uns16 max_retries);

  rs_bool pl_dd_get_timeout (int16 hcam, uns16_ptr m_sec);
  rs_bool pl_dd_set_timeout (int16 hcam, uns16 m_sec);

  rs_bool pl_ccd_get_adc_offset (int16 hcam, int16_ptr offset);
  rs_bool pl_ccd_set_adc_offset (int16 hcam, int16 offset);

  rs_bool pl_ccd_get_chip_name (int16 hcam, char_ptr chip_name);

  rs_bool pl_ccd_get_clear_cycles (int16 hcam, uns16_ptr clear_cycles);
  rs_bool pl_ccd_set_clear_cycles (int16 hcam, uns16 clr_cycles);

  rs_bool pl_ccd_get_clear_mode (int16 hcam, int16_ptr clear_mode);
  rs_bool pl_ccd_set_clear_mode (int16 hcam, int16 ccd_clear);

  rs_bool pl_ccd_get_color_mode (int16 hcam, uns16_ptr color_mode);

  rs_bool pl_ccd_get_cooling_mode (int16 hcam, int16_ptr cooling);

  rs_bool pl_ccd_get_frame_capable (int16 hcam,
                                            rs_bool_ptr frame_capable);

  rs_bool pl_ccd_get_fwell_capacity (int16 hcam,
                                             uns32_ptr fwell_capacity);

  rs_bool pl_ccd_get_mpp_capable (int16 hcam, int16_ptr mpp_capable);

  rs_bool pl_ccd_get_preamp_dly (int16 hcam, uns16_ptr preamp_dly);

  rs_bool pl_ccd_get_preamp_off_control (int16 hcam,
                                                 uns32_ptr preamp_off_control);
  rs_bool pl_ccd_set_preamp_off_control (int16 hcam,
                                                 uns32 preamp_off_control);

  rs_bool pl_ccd_get_preflash (int16 hcam, uns16_ptr pre_flash);

  rs_bool pl_ccd_get_pmode (int16 hcam, int16_ptr pmode);
  rs_bool pl_ccd_set_pmode (int16 hcam, int16 pmode);

  rs_bool pl_ccd_get_premask (int16 hcam, uns16_ptr pre_mask);

  rs_bool pl_ccd_get_prescan (int16 hcam, uns16_ptr prescan);

  rs_bool pl_ccd_get_postmask (int16 hcam, uns16_ptr post_mask);

  rs_bool pl_ccd_get_postscan (int16 hcam, uns16_ptr postscan);

  rs_bool pl_ccd_get_par_size (int16 hcam, uns16_ptr par_size);

  rs_bool pl_ccd_get_ser_size (int16 hcam, uns16_ptr ser_size);

  rs_bool pl_ccd_get_serial_num (int16 hcam, uns16_ptr serial_num);

  rs_bool pl_ccs_get_status (int16 hcam, int16_ptr ccs_status);

  rs_bool pl_ccd_get_summing_well (int16 hcam,
                                           rs_bool_ptr s_well_exists);

  rs_bool pl_ccd_get_tmp (int16 hcam, int16_ptr cur_tmp);
  rs_bool pl_ccd_get_tmp_range (int16 hcam, int16_ptr tmp_hi_val,
                                        int16_ptr tmp_lo_val);

  rs_bool pl_ccd_get_tmp_setpoint (int16 hcam, int16_ptr tmp_setpoint);
  rs_bool pl_ccd_set_tmp_setpoint (int16 hcam, int16 tmp_setpoint);

  rs_bool pl_ccd_set_readout_port (int16 , int16 );
  rs_bool pl_ccd_get_pix_par_dist (int16 hcam, uns16_ptr pix_par_dist);

  rs_bool pl_ccd_get_pix_par_size (int16 hcam, uns16_ptr pix_par_size);

  rs_bool pl_ccd_get_pix_ser_dist (int16 hcam, uns16_ptr pix_ser_dist);

  rs_bool pl_ccd_get_pix_ser_size (int16 hcam, uns16_ptr pix_ser_size);

  rs_bool pl_spdtab_get_bits (int16 hcam, int16_ptr spdtab_bits);

  rs_bool pl_spdtab_get_gain (int16 hcam, int16_ptr spdtab_gain);
  rs_bool pl_spdtab_set_gain (int16 hcam, int16 spdtab_gain);
  rs_bool pl_spdtab_get_max_gain (int16 hcam,
                                          int16_ptr spdtab_max_gain);

  rs_bool pl_spdtab_get_num (int16 hcam, int16_ptr spdtab_num);
  rs_bool pl_spdtab_set_num (int16 hcam, int16 spdtab_num);

  rs_bool pl_spdtab_get_entries (int16 hcam, int16_ptr spdtab_entries);

  rs_bool pl_spdtab_get_port (int16 hcam, int16_ptr spdtab_port);
  rs_bool pl_spdtab_get_port_total (int16 hcam, int16_ptr total_ports);

  rs_bool pl_spdtab_get_time (int16 hcam, uns16_ptr spdtab_time);

  rs_bool pl_shtr_get_close_dly (int16 hcam, uns16_ptr shtr_close_dly);
  rs_bool pl_shtr_set_close_dly (int16 hcam, uns16 shtr_close_dly);

  rs_bool pl_shtr_get_open_dly (int16 hcam, uns16_ptr shtr_open_dly);
  rs_bool pl_shtr_set_open_dly (int16 hcam, uns16 shtr_open_dly);

  rs_bool pl_shtr_get_open_mode (int16 hcam, int16_ptr shtr_open_mode);
  rs_bool pl_shtr_set_open_mode (int16 hcam, int16 shtr_open_mode);

  rs_bool pl_shtr_get_status (int16 hcam, int16_ptr shtr_status);

  rs_bool pl_exp_get_time_seq (int16 hcam, uns16_ptr exp_time);
  rs_bool pl_exp_set_time_seq (int16 hcam, uns16 exp_time);

  rs_bool pl_exp_check_progress (int16 hcam, int16_ptr status,
                                         uns32_ptr bytes_arrived);






  rs_bool pl_exp_set_cont_mode (int16 hcam, int16 mode);
  rs_bool pl_subsys_do_diag (int16 hcam, uns8 subsys_id,
                                     uns16_ptr err_code);
  rs_bool pl_subsys_get_id (int16 hcam, uns8 subsys_id,
                                    uns16_ptr part_num, uns8_ptr revision);
  rs_bool pl_subsys_get_name (int16 hcam, uns8 subsys_id,
                                      char_ptr subsys_name);
