import pandas as pd


def _format_euro(amount: float) -> str:
    return f"{amount:,.0f} €".replace(",", "_").replace("_", ",")


def answer(question: str, df: pd.DataFrame) -> dict:
    q = question.strip().lower()

    if df is None or df.empty:
        return {
            "text": (
                "Nessun dato disponibile al momento. "
                "Aggiungi un file CSV con i dati nella cartella del progetto e ricarica l'app."
            )
        }

    sold = df[df["is_venduto"]]

    if "venduto" in q:
        total = sold["ricavo_2026"].sum()
        return {"text": f"Venduto 2026 totale: {_format_euro(total)}."}

    if "pipeline" in q:
        total = df["pipeline_pesata_2026"].sum()
        return {"text": f"Pipeline pesata 2026 totale: {_format_euro(total)}."}

    if "top" in q and "client" in q:
        if sold.empty:
            return {"text": "Non ci sono opportunità vendute nel perimetro filtrato."}

        top_clients = (
            sold.groupby("cliente_codice", as_index=False)["ricavo_2026"]
            .sum()
            .sort_values("ricavo_2026", ascending=False)
            .head(10)
        )
        return {
            "text": "Top 10 clienti per venduto 2026.",
            "chart": ("bar", top_clients, "cliente_codice", "ricavo_2026"),
        }

    if "servizi" in q or "service" in q:
        if sold.empty:
            return {"text": "Non ci sono opportunità vendute nel perimetro filtrato."}

        top_services = (
            sold.groupby("Servizi A&M", as_index=False)["ricavo_2026"]
            .sum()
            .sort_values("ricavo_2026", ascending=False)
            .head(15)
        )
        return {
            "text": "Top servizi per ricavo 2026.",
            "chart": ("bar", top_services, "Servizi A&M", "ricavo_2026"),
        }

    return {
        "text": (
            "Domanda non riconosciuta. Prova con un quesito come "
            "'Venduto 2026', 'Pipeline pesata' o 'Top clienti'."
        )
    }
