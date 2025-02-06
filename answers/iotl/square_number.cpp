void setup() {
<<<<<<< HEAD
=======
  // put your setup code here, to run once:
>>>>>>> c8dd21eb2c04b4946330ee3006197fde53b2ba40
  Serial.begin(9600);
  Serial.println("Input a number:");
}

void loop() {
<<<<<<< HEAD
  if (Serial.available() > 0) {
    int input = Serial.parseInt();
    if (input != 0) {
      int inputSquared = square(input);
      Serial.print("Squared: ");
      Serial.println(inputSquared);
=======
  // put your main code here, to run repeatedly:
  
  // Wait until there's some input in the serial buffer
  if (Serial.available() > 0) {
    int input = Serial.parseInt(); // Read the input number from the serial monitor
    
    // Check if a valid number was entered
    if (input != 0) {
      int inputSquared = square(input);  // Use the new square function
      Serial.print("Squared: ");
      Serial.println(inputSquared);    // Output the squared value
>>>>>>> c8dd21eb2c04b4946330ee3006197fde53b2ba40
    } else {
      Serial.println("Please enter a valid number.");
    }
  }
<<<<<<< HEAD
  delay(500);
}

=======

  delay(500);  // Wait for 500ms before checking again
}

// Define a new function to square the input number
>>>>>>> c8dd21eb2c04b4946330ee3006197fde53b2ba40
int square(int num) {
  return num * num;
}
