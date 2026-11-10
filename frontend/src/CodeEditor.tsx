import {useEffect,useRef} from 'react';
import {EditorView,basicSetup} from 'codemirror';
import {keymap} from '@codemirror/view';
import {indentWithTab} from '@codemirror/commands';
import {python} from '@codemirror/lang-python';
import {javascript} from '@codemirror/lang-javascript';
import {json} from '@codemirror/lang-json';
import {html} from '@codemirror/lang-html';
import {css} from '@codemirror/lang-css';
import {oneDark} from '@codemirror/theme-one-dark';
export default function CodeEditor({path,value,onChange,onSave}:{path:string;value:string;onChange:(s:string)=>void;onSave:()=>void}){
 const host=useRef<HTMLDivElement>(null),view=useRef<EditorView|null>(null),change=useRef(onChange),save=useRef(onSave);change.current=onChange;save.current=onSave;
 useEffect(()=>{const language=path.endsWith('.py')?python():/\.[jt]sx?$/.test(path)?javascript({typescript:/\.tsx?$/.test(path),jsx:/x$/.test(path)}):path.endsWith('.json')?json():path.endsWith('.html')?html():path.endsWith('.css')?css():[];
 const editor=new EditorView({doc:value,parent:host.current!,extensions:[basicSetup,language,oneDark,keymap.of([{key:'Mod-s',run:()=>{save.current();return true;}},indentWithTab]),EditorView.updateListener.of(update=>{if(update.docChanged)change.current(update.state.doc.toString());}),EditorView.theme({'&':{height:'520px',fontSize:'14px'},'.cm-scroller':{overflow:'auto'}}),EditorView.contentAttributes.of({'aria-label':'Quellcode bearbeiten'})]});view.current=editor;return()=>{editor.destroy();view.current=null;};},[path]);
 useEffect(()=>{const e=view.current;if(e&&e.state.doc.toString()!==value)e.dispatch({changes:{from:0,to:e.state.doc.length,insert:value}});},[value]);
 return <div className="code-editor" ref={host}/>;
}
