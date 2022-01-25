
const int output_pin = 4;
const int pulse_length = 10;
const int inter_pulse_interval = 1000;  // 5 seconds


void setup() {
  pinMode(output_pin, OUTPUT);
  digitalWrite(output_pin, LOW);
}


void loop() {
  digitalWrite(output_pin, HIGH);
  delay(pulse_length);
  digitalWrite(output_pin, LOW);
  delay(inter_pulse_interval);
}
