export type Spec={id?:number;key:string;name:string;method_id:number;method?:string;unit:string;kind:'numeric'|'qualitative';count:number;labels:string[];lsl:string|null;usl:string|null;lower_inclusive:boolean;upper_inclusive:boolean;decimals:number;frequency:'every'|'nth'|'extra';every_n:number;allowed:string[];passing:string[];simulation_offset:string|null};
export type Article={id:number;code:string;name:string;cycle:number};
export type Order={id:number;article_id:number;article:string;code:string;lot:string;roll:string;quantity:string;status:string;created:string;completed:string|null;required_sessions:number;extra:string[];history:{held:boolean;reason:string;author:string;date:string}[]};
export type Plan={article:string;code:string;cycle:number;config_id:number;version:number;specs:Spec[]};
export type LabResult={id:number;order_id:number;revision:number;article:string;code:string;lot:string;roll:string;test_date:string;cycle:number;operator:string;source:string;label:string;config_id:number;ok:boolean;metadata:Record<string,string>;correction_of:number|null;reason:string;results:{spec:Spec;values:string[];average:string|null;ok:boolean;individual_ok:boolean[];transforms:{corrected:boolean;parameters:{outcome:string}}[]}[]};
export type User={login:string;role:string;csrf:string;permissions:string[]};
export type Method={id:number;code:string;name:string};

/** Wstępna ocena interfejsu. Zapis zawsze przelicza backend z Decimal. */
export function inSpec(value:number,s:Spec){return (s.lsl===null||(s.lower_inclusive?value>=Number(s.lsl):value>Number(s.lsl)))&&(s.usl===null||(s.upper_inclusive?value<=Number(s.usl):value<Number(s.usl)));}
/** Sprawdza wszystkie pola, także dziesiąty punkt pomiarowy. */
export function complete(specs:Spec[],values:Record<string,string[]>){return specs.length>0&&specs.every(s=>values[s.key]?.length===s.count&&values[s.key].every(v=>v.trim()!==''&&(s.kind==='numeric'?Number.isFinite(Number(v.replace(',','.'))):s.allowed.includes(v))));}
