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


export const BOARDS: BoardDef[] = [PI5];

// mcphardware/src/lib/boards.ts
export const PARTS: PartDef[] = [
  { id: 'led',    name: 'LED',                   roles: ['Light'],                 minPins: 1, maxPins: 1 },
  { id: 'button', name: 'Button',                roles: ['Press'],                 minPins: 1, maxPins: 1 },
  { id: 'relay',  name: 'Relay',                 roles: ['Switch'],                minPins: 1, maxPins: 1 },
  { id: 'buzzer', name: 'Buzzer',                roles: ['Buzz'],                  minPins: 1, maxPins: 1 },
  { id: 'dht22',  name: 'DHT22 (Temp/Humidity)', roles: ['Temperature','Humidity'],minPins: 1, maxPins: 1 },
  { id: 'hcsr04', name: 'HC-SR04 (Ultrasonic)',  roles: ['Trigger','Echo'],       minPins: 2, maxPins: 2 },
  { id: 'custom', name: 'Custom (multi-pin)',    roles: ['Generic'],              minPins: 1, maxPins: 6 },
];
