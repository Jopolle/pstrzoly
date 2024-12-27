//YWROBOT
//Compatible with the Arduino IDE 1.0
//Library version:1.1
/*
SDA - A4
SCL - A5
*/
#include <LiquidCrystal_I2C.h>
#include <SD.h>
#include <SPI.h>

Sd2Card card;                                                             // set up variables using the SD utility library functions
SdVolume volume;
SdFile root;

const int chipSelect = 9; 


LiquidCrystal_I2C lcd(0x27,16,2);  // set the LCD address to 0x27 for a 16 chars and 2 line display
File myFile;
void setup()
{
  lcd.init();                      // initialize the lcd 
  // Print a message to the LCD.
  lcd.backlight();
  lcd.setCursor(0,0);
  lcd.print("Hello everybody");
  lcd.setCursor(0,1);
  lcd.print("bruh");
  Serial.begin(9600);
  while (!Serial){
    ;
  }


  Serial.print("Initializing SD card...\n");

  if (!card.init(SPI_HALF_SPEED, chipSelect)) {                            // Initialize and check SD card
    Serial.print("SD initialisation failed \n");
  }else{
    Serial.print("Wiring is correct and a card is present.\n");
  }
  //SPI.transfer(0);
  if(SD.begin(chipSelect)){
    Serial.print("Begin udane");
  }
  // open the file. note that only one file can be open at a time,
  // so you have to close this one before opening another.
  myFile = SD.open("test.txt", FILE_WRITE);

  // if the file opened okay, write to it:
  if (myFile) {
    Serial.print("Writing to test.txt...");
    myFile.println("testing 1, 2, 3.");
    // close the file:
    myFile.close();
    Serial.println("done.");
  } else {
    // if the file didn't open, print an error:
    Serial.println("error opening test.txt");
  }

  // re-open the file for reading:
  myFile = SD.open("test.txt");
  if (myFile) {
    Serial.println("test.txt:");

    // read from the file until there's nothing else in it:
    while (myFile.available()) {
      lcd.setCursor(0,0);
      lcd.print(Serial.write(myFile.read()));
    }
    // close the file:
    myFile.close();
  } else {
    // if the file didn't open, print an error:
    Serial.println("error opening test.txt");
  }



}


void loop()
{
}
