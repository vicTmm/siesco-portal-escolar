"use client";
export default function ErrorPage({ reset }: { reset: () => void }) {
  return <main className="fatal"><h1>Não foi possível abrir esta página.</h1><p>Tente carregar novamente.</p><button onClick={reset}>Tentar novamente</button></main>;
}
