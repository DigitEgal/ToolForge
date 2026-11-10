export default function DigitEgalLogo({compact=false}:{compact?:boolean}){
 return <span className={compact?'digitegal compact':'digitegal'} aria-label="by DigitEgal">
  <svg viewBox="0 0 32 32" aria-hidden="true">
   <path d="M5 5h10a11 11 0 0 1 0 22H5V5Zm6 5v12h4a6 6 0 0 0 0-12h-4Z" fill="currentColor"/>
   <path d="M22 9h5v14h-5z" fill="currentColor" opacity=".55"/>
  </svg>
  <span>by <strong>DigitEgal</strong></span>
 </span>;
}
