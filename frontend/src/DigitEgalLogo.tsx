import DigitEgalWordmark from '../logos/LogoV6_textONLY.png';

export default function DigitEgalLogo({compact=false}:{compact?:boolean}){
  return <a className={compact?'digitegal compact':'digitegal'} href="https://digitegal.de" target="_blank" rel="noopener noreferrer" title="DigitEgal im Browser öffnen">
    <span>by</span><img className="digitegal-wordmark" src={DigitEgalWordmark} alt="DigitEgal" />
  </a>;
}
