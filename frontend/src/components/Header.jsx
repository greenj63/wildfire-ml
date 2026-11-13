export default function Header() {
  return (
    <header className="header">
      <h1>Wildfire Severity Predictor</h1>
      <div className="formula-wrap">
        {/* Decorative: sits behind the formula, which is the text that matters */}
        <img className="molecule" src="/images/molecule.png" alt="" />
        <span className="formula">
          C<sub>8</sub>H<sub>11</sub>NO<sub>2</sub>
        </span>
      </div>
    </header>
  );
}
