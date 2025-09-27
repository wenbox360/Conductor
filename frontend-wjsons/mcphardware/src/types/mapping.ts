export type Mapping = {
  id: string;
  boardId: string;
  partId: string;
  role: string;
  pins: number[];   // single-pin now, but keep array for future-proof
  label?: string;
};
