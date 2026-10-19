import time, gc, machine
def t(name, fn, n=5):
  s = time.ticks_us()
  for _ in range(n): fn()
  print(name, time.ticks_diff(time.ticks_us(), s) // n, "us")
a = machine.ADC(machine.ADC.CORE_TEMP)
t("mem_free", gc.mem_free); t("mem_alloc", gc.mem_alloc)
t("disk_free", badge.disk_free); t("batt_v", badge.battery_voltage)
t("batt_lvl", badge.battery_level); t("light", badge.light_level)
t("charging", badge.is_charging); t("freq", machine.freq); t("adc", a.read_u16)
t("caselights", lambda: badge.caselights(0.1, 0.2, 0.3, 0.4))
badge.caselights(0)
