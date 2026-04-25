declare module 'point-in-polygon' {
  function pointInPolygon(
    point: number[],
    polygon: number[][],
    vs?: 'x' | 'y'
  ): boolean
  export default pointInPolygon
}
