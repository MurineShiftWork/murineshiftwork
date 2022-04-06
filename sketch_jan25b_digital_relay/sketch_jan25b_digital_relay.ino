
const int input_pin = 8;
const int output_pin_range_start = 2;
const int output_pin_range_end = 7;

const int pulse_length = 5;

int input_reading = LOW;
long debounce_check_time = 0;
long debounce_delay = 50;


void set_multi_pin( int from_pin, int to_pin, int new_status){
  for(int i = from_pin; i <= to_pin; i++){
    digitalWrite(i, new_status);
  }
}

void send_trigger() {
  set_multi_pin(output_pin_range_start, output_pin_range_end, HIGH);
  delay(pulse_length);
  set_multi_pin(output_pin_range_start, output_pin_range_end, LOW);
}


void setup() {
  // set up input pin
  pinMode(input_pin, INPUT);

  // set up output pin range
  for(int i = output_pin_range_start; i <= output_pin_range_end; i++){
    pinMode(i, OUTPUT);
    digitalWrite(i, LOW);
  }

  // serial for debugging
  Serial.begin(9600);
  Serial.println("Set up.");

}


void loop() {
  input_reading = digitalRead(input_pin);

  if ( (millis()-debounce_check_time ) > debounce_delay ) {

    if (input_reading == HIGH) {
      // serial for debugging
      Serial.print(millis());
      Serial.println("Sending trigger");

      // send trigger
      send_trigger();

      // stop monitoring until debounced
      debounce_check_time = millis();
    }

  }

}
