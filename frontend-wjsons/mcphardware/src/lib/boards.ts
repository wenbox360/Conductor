// File: mcphardware/src/lib/boards.ts
export type HeaderRect = {   // % of the image (0..1)
  x: number; y: number; w: number; h: number;  // top-left + width/height
  columns?: 2 | 1; // default 2 for 2×20 headers
};

export type BoardDef = {
  id: string;
  name: string;
  image: string;        // /boards/pi40.jpg (put your real photo here)
  header: HeaderRect;   // where the 2×20 header sits on the image
  rows: number;         // 20 for Pi
  oddLabels?: Record<number,string>;
  evenLabels?: Record<number,string>;
  gnd?: number[];
  v33?: number[];
  v5?: number[];
  // Custom layout for non-standard boards
  customLayout?: {
    type: 'arduino' | 'custom';
    pinGroups: Array<{
      startPin: number;
      endPin: number;
      x: number;        // 0-1 relative to image
      y: number;        // 0-1 relative to image
      width: number;    // 0-1 relative to image
    }>;
  };
};

export type PartDef = {
  id: string;
  name: string;
  roles: string[];
  minPins?: number;
  maxPins?: number;
  pinCount?: number;
};

// Raspberry Pi 4/5 — tweak header rect to match your photo.
// The numbers below assume a fairly standard top-down photo; adjust once you add your image.
export const PI40: BoardDef = {
  id: 'pi40',
  name: 'Raspberry Pi 4/5 (40-pin)',
  image: '/boards/pi40.jpg',      // <- add this file in /public/boards
  header: { x: 0.36, y: 0.08, w: 0.09, h: 0.78, columns: 2 }, // rectangle over the header
  rows: 20,
  v5: [2,4],
  v33: [1,17],
  gnd: [6,9,14,20,25,30,34,39],
  oddLabels: { 1:'3V3', 3:'GPIO2', 5:'GPIO3', 7:'GPIO4', 9:'GND', 11:'GPIO17', 13:'GPIO27', 15:'GPIO22', 17:'3V3', 19:'GPIO10', 21:'GPIO9', 23:'GPIO11', 25:'GND', 27:'ID_SD', 29:'GPIO5', 31:'GPIO6', 33:'GPIO13', 35:'GPIO19', 37:'GPIO26', 39:'GND' },
  evenLabels: { 2:'5V', 4:'5V', 6:'GND', 8:'GPIO14', 10:'GPIO15', 12:'GPIO18', 14:'GND', 16:'GPIO23', 18:'GPIO24', 20:'GND', 22:'GPIO25', 24:'GPIO8', 26:'GPIO7', 28:'ID_SC', 30:'GND', 32:'GPIO12', 34:'GND', 36:'GPIO16', 38:'GPIO20', 40:'GPIO21' },
};


// --- New: Raspberry Pi 5 (40-pin) ------------------------
export const PI5: BoardDef = {
  id: 'pi5',
  name: 'Raspberry Pi 5 (40-pin)',
  image: '/boards/pi5.jpg',
  // Header rectangle is expressed as percentages of the rendered image (0..1)
  // Tuned for the provided photo: top header, left→right across the board.
  header: { x: 0.103, y: 0.000, w: 0.555, h: 0.138, columns: 2 },
  rows: 20,
  // Standard 40-pin labels (same logical mapping as Pi 4/5)
  v5: [2,4],
  v33: [1,17],
  gnd: [6,9,14,20,25,30,34,39],
  oddLabels: {
    1:'3V3', 3:'GPIO2', 5:'GPIO3', 7:'GPIO4', 9:'GND', 11:'GPIO17', 13:'GPIO27',
    15:'GPIO22', 17:'3V3', 19:'GPIO10', 21:'GPIO9', 23:'GPIO11', 25:'GND',
    27:'ID_SD', 29:'GPIO5', 31:'GPIO6', 33:'GPIO13', 35:'GPIO19', 37:'GPIO26', 39:'GND'
  },
  evenLabels: {
    2:'5V', 4:'5V', 6:'GND', 8:'GPIO14', 10:'GPIO15', 12:'GPIO18', 14:'GND',
    16:'GPIO23', 18:'GPIO24', 20:'GND', 22:'GPIO25', 24:'GPIO8', 26:'GPIO7',
    28:'ID_SC', 30:'GND', 32:'GPIO12', 34:'GND', 36:'GPIO16', 38:'GPIO20', 40:'GPIO21'
  }
};


// --- Arduino Leonardo R3 (31-pin) ------------------------
export const ARDUINO_LEONARDO: BoardDef = {
  id: 'leonardo',
  name: 'Arduino Leonardo R3',
  image: '/boards/leonardo.png',
  // Standard header for fallback
  header: { x: 0.15, y: 0.25, w: 0.7, h: 0.5 },
  rows: 31, // 31 pins total (18 top + 13 bottom right)
  v5: [22], // 5V pin (bottom right)
  v33: [21], // 3.3V pin (bottom right)
  gnd: [4, 23, 24], // GND pins (top and bottom right)
  oddLabels: {
    1: 'SCL', 3: 'AREF', 5: '~13', 7: '~11', 9: '~9', 11: '7', 13: '~5', 15: '~3', 17: 'TX1', 19: 'IOREF', 21: '3.3V', 23: 'GND', 25: 'Vin', 27: 'A1', 29: 'A3', 31: 'A5'
  },
  evenLabels: {
    2: 'SDA', 4: 'GND', 6: '12', 8: '~10', 10: '8', 12: '~6', 14: '4', 16: '2', 18: 'RX0', 20: 'RESET', 22: '5V', 24: 'GND', 26: 'A0', 28: 'A2', 30: 'A4'
  },
  // Custom Arduino layout
  customLayout: {
    type: 'arduino',
    pinGroups: [
      {
        startPin: 1,
        endPin: 18,
        x: 0.08,   // Top row position
        y: 0.18,   // Top row Y
        width: 0.84 // Top row width
      },
      {
        startPin: 19,
        endPin: 31,
        x: 0.35,   // Bottom row position (moved more to the right)
        y: 0.80,   // Bottom row Y (around 80% down from top)
        width: 0.48 // Bottom row width (spans about 48% of board width)
      }
    ]
  }
};

export const BOARDS: BoardDef[] = [PI5, ARDUINO_LEONARDO];

// mcphardware/src/lib/boards.ts
export const PARTS: PartDef[] = [
  { id: 'led',    name: 'LED',                   roles: ['Light'],                 minPins: 1, maxPins: 1 },
  { id: 'button', name: 'Button',                roles: ['Press'],                 minPins: 1, maxPins: 1 },
  { id: 'relay',  name: 'Relay',                 roles: ['Switch'],                minPins: 1, maxPins: 1 },
  { id: 'buzzer', name: 'Buzzer',                roles: ['Buzz'],                  minPins: 1, maxPins: 1 },
  { id: 'dht22',  name: 'DHT22 (Temp/Humidity)', roles: ['Temperature','Humidity'],minPins: 1, maxPins: 1 },
  { id: 'hcsr04', name: 'HC-SR04 (Ultrasonic)',  roles: ['Trigger','Echo'],       minPins: 2, maxPins: 2 },
  { id: 'servo',  name: 'Servo Motor',           roles: ['Control'],               minPins: 1, maxPins: 1 },
  { id: 'analog_sensor', name: 'Analog Sensor',  roles: ['Read'],                  minPins: 1, maxPins: 1 },
  { id: 'digital_sensor', name: 'Digital Sensor', roles: ['Read'],                 minPins: 1, maxPins: 1 },
  { id: 'custom', name: 'Custom (multi-pin)',    roles: ['Generic'],              minPins: 1, maxPins: 6 },
];
