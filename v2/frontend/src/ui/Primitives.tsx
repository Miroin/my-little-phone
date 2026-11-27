import type {ButtonHTMLAttributes,HTMLAttributes,InputHTMLAttributes,ReactNode,SelectHTMLAttributes,TextareaHTMLAttributes} from 'react';

const classes=(...values:(string|false|undefined)[])=>values.filter(Boolean).join(' ');

type ButtonProps=ButtonHTMLAttributes<HTMLButtonElement>&{tone?:'primary'|'secondary'|'quiet'|'danger'};
export function Button({tone='primary',className,...props}:ButtonProps){return <button className={classes('ui-button',tone!=='primary'&&`ui-button--${tone}`,className)} {...props}/>;}

type FieldProps={label:string;hint?:string;children:ReactNode;className?:string};
export function Field({label,hint,children,className}:FieldProps){return <label className={classes('ui-field',className)}><span>{label}</span>{children}{hint&&<small>{hint}</small>}</label>;}

export function Input({className,...props}:InputHTMLAttributes<HTMLInputElement>){return <input className={classes('ui-input',className)} {...props}/>;}
export function Textarea({className,...props}:TextareaHTMLAttributes<HTMLTextAreaElement>){return <textarea className={classes('ui-textarea',className)} {...props}/>;}
export function Select({className,...props}:SelectHTMLAttributes<HTMLSelectElement>){return <select className={classes('ui-select',className)} {...props}/>;}

type StatusProps=HTMLAttributes<HTMLDivElement>&{tone?:'info'|'success'|'warning'|'error'};
export function Status({tone='info',className,...props}:StatusProps){return <div role={tone==='error'?'alert':'status'} className={classes('ui-status',tone!=='info'&&`ui-status--${tone}`,className)} {...props}/>;}

type SheetProps={title:string;onClose:()=>void;children:ReactNode;className?:string};
export function Sheet({title,onClose,children,className}:SheetProps){return <div className="ui-overlay" role="presentation"><section className={classes('ui-sheet',className)} role="dialog" aria-modal="true" aria-label={title}><header className="ui-sheet__head"><h2>{title}</h2><button className="ui-icon-button" type="button" onClick={onClose} aria-label="关闭">×</button></header><div className="ui-sheet__body">{children}</div></section></div>;}
