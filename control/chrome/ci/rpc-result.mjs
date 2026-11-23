// Keep the service's exact JSON byte count, before parsing loses escapes or
// number formatting. Metadata must not become part of the result or its logs.
export function rpcResult(line){
  return Object.defineProperty(JSON.parse(line),'wireBytes',{value:Buffer.byteLength(line)});
}
