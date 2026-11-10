import ToolForgeLogo from '../logos/LogoV7_OnlyLOGO.png';

export default function BrandMark({className = ''}: {className?: string}) {
  return <img src={ToolForgeLogo} alt="" aria-hidden="true"
    className={`brand-logo${className ? ` ${className}` : ''}`} />;
}
