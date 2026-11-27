; ldc / ldc_w / ldc2_w with all kinds of constants
.class public Constants
.super java/lang/Object

.method public static test()V
  .limit stack 10
  .limit locals 2
  ldc 1
  ldc -1
  ldc 2147483647
  ldc 3000000000
  ldc 0x10
  ldc 1.5
  ldc 0.1
  ldc 3.4028235e38
  ldc 1.0e39
  ldc 1.0e-40
  ldc 1.0e-46
  ldc -0.0
  ldc 0.0
  ldc 1.5d
  ldc 100.0
  ldc 1234567.0
  ldc 12345678.0
  ldc 0.001
  ldc 0.0001
  ldc 1.17549435E-38
  ldc "a string"
  ldc "unicode ü中"
  ldc "zero \0 byte"
  ldc java/lang/String
  ldc_w 2
  ldc_w 2.5
  ldc_w "w"
  ldc_w java/lang/Integer
  ldc2_w 1
  ldc2_w 123456789012345
  ldc2_w 0.1
  ldc2_w 0.1d
  ldc2_w 1.0e300
  ldc2_w -2.5
  ldc2_w -0x1.8p1
  ldc2_w 4.9E-324d
  ldc2_w 1.7976931348623157E308
  ldc2_w 123456789.123456789d
  ldc2_w 2.2250738585072014E-308d
  return
.end method
