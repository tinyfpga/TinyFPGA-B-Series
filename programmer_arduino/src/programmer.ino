#include <SPI.h>

// SS:   pin 10
// MOSI: pin 11
// MISO: pin 12
// SCK:  pin 13


void setup(void) {
    SPI.begin();
    SPI.setDataMode(0);
    SPI.setBitOrder(MSBFIRST);

    Serial.begin(115200);
}


void serial_read(unsigned char * buf, int length) {
    while(!Serial.available()) {}
    Serial.readBytes(buf, length);
}


void loop(void) {
    unsigned char opcode, write_lo, write_hi, read_lo, read_hi;
    unsigned char write_buf[130], read_buf[130];

    serial_read(&opcode, 1);
    if(opcode == 0x01) {  // access SIP command

        // read parameters from serial
        serial_read(&write_lo, 1);
        serial_read(&write_hi, 1);
        serial_read(&read_lo, 1);
        serial_read(&read_hi, 1);
        if(write_lo > 128 || write_hi != 0 || read_lo > 128 || read_hi != 0) {
            return;  // abort
        }
        serial_read(write_buf, write_lo);

        // SPI communication
        digitalWrite(SS, HIGH);
        digitalWrite(SS, LOW);
        for(unsigned char i = 0; i < write_lo; i++) {
            SPI.transfer(write_buf[i]);
        }
        for(unsigned char i = 0; read_lo && i < read_lo - 1; i++) {
            read_buf[i] = SPI.transfer(0);
        }
        digitalWrite(SS, HIGH);

        // send reply to serial
        if(read_lo) {
            Serial.write(read_buf, read_lo - 1);
        }
    } else {
        // ignore other opcodes (e.g. boot)
    }
}
