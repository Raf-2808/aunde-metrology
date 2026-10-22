export class ApiError extends Error {constructor(public status:number,message:string){super(message);}}
let csrf='';
export function setCsrf(value:string){csrf=value;}
/** Centralizuje obsługę sesji HTTP-only i tokena CSRF. */
export async function api<T=unknown>(path:string,method='GET',body?:unknown):Promise<T>{
  const form=body instanceof FormData;
  const r=await fetch('/api'+path,{method,credentials:'same-origin',headers:{...(body&&!form?{'Content-Type':'application/json'}:{}),'X-CSRF-Token':csrf},body:body?(form?body:JSON.stringify(body)):undefined});
  if(!r.ok){const e=await r.json().catch(()=>({detail:r.statusText}));throw new ApiError(r.status,typeof e.detail==='string'?e.detail:JSON.stringify(e.detail));}
  return r.json();
}
