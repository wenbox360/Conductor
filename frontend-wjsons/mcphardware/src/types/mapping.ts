export type Mapping = {
  id: string;
  boardId: string;
  partId: string;
  role: string;
  pins: (number | string)[];   // can be numbers (like 13) or strings (like 'A0', 'SDA')
  label?: string;
};
