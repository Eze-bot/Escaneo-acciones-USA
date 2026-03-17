# --- MOSTRAR RESULTADOS ---
    cols = st.columns(2)
    for i, res in enumerate(res_finales):
        with cols[i % 2]:
            sent_label = "pos-label" if res['News'] == "POS" else ("neg-label" if res['News'] == "NEG" else "neu-label")
            # ASEGÚRATE DE COPIAR DESDE AQUÍ HASTA EL PARÉNTESIS FINAL
            st.markdown(f"""
                <div class="ticker-card">
                    <h3>{res['Ticker']} - ${res['Precio']}</h3>
                    <p>Confianza: <b>{res['Confianza']}/100</b> | GAP: +{res['Gap %']}%</p>
                    <p>Noticias: <span class="{sent_label}">{res['News']}</span> | RSI: {res['RSI']}</p>
                    <p style="color:red"><b>SL Sugerido: ${res['SL']}</b></p>
                </div>
            """, unsafe_allow_html=True)
            st.line_chart(res['ChartData'])
