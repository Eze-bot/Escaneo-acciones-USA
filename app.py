# --- GRÁFICO PROFESIONAL CON EJE X LIMPIO ---
        fig = go.Figure()

        # Línea de Precio
        fig.add_trace(go.Scatter(
            x=r['df_plot'].index, y=r['df_plot']['Close'],
            name="Precio", line=dict(color='#1A73E8', width=3),
            hovertemplate="Fecha: %{x}<br>Precio: $%{y:.2f}<extra></extra>"
        ))

        # Línea de RSI (Eje Secundario)
        fig.add_trace(go.Scatter(
            x=r['df_plot'].index, y=r['rsi_plot'],
            name="RSI", line=dict(color='#D93025', width=1.5, dash='dot'),
            yaxis="y2",
            hovertemplate="RSI: %{y:.1f}<extra></extra>"
        ))

        fig.update_layout(
            height=280,
            margin=dict(l=10, r=10, t=20, b=20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            showlegend=False,
            # CONFIGURACIÓN DEL EJE X PARA EVITAR AMONTONAMIENTO
            xaxis=dict(
                showgrid=False,
                tickmode='auto',
                nticks=5, # <--- FUERZA A MOSTRAR MÁXIMO 5 FECHAS COMO REFERENCIA
                tickfont=dict(size=10, color="#5f6368"),
                linecolor='#eeeeee'
            ),
            yaxis=dict(
                showgrid=True, 
                gridcolor='#f0f0f0',
                tickfont=dict(size=10),
                title=dict(text="Precio $", font=dict(size=10))
            ),
            yaxis2=dict(
                overlaying='y', side='right', range=[0, 100], 
                showgrid=False, tickfont=dict(size=10, color='#D93025')
            )
        )
        
        # Importante: usar una key única para evitar el error de duplicados
        st.plotly_chart(fig, use_container_width=True, key=f"plot_{r['Ticker']}_{i}", config={'displayModeBar': False})
