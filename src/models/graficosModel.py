import matplotlib.pyplot as plt
import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class GraficosModel:
    def graficos(self, resultados_por_padrao, master=None):
        """resultados_por_padrao: {rótulo do padrão: [concentracoes, areas_normalizadas, ...]}."""
        rotulos = list(resultados_por_padrao)
        self.concentracoes = resultados_por_padrao[rotulos[0]][0]
        self.areas_norm = resultados_por_padrao[rotulos[0]][1]
        # print(self.concentracoes)
        # print(self.areas_norm)

        # cria uma nova janela (aba) sobre a janela principal
        config_graficos = ctk.CTkToplevel(master)
        config_graficos.title("Configurar Gráficos")
        config_graficos.geometry("1000x800")
        config_graficos.focus_force()
        config_graficos.grab_set()  # impede interação com a janela principal enquanto aberta

        # centraliza a nova aba
        largura, altura = 1000, 800
        x = (config_graficos.winfo_screenwidth() // 2) - (largura // 2)
        y = (config_graficos.winfo_screenheight() // 2) - (altura // 2)
        config_graficos.geometry(f"{largura - 180}x{altura - 300}+{x}+{y}")

        # --- seleção da amostra ---
        selecione_amostra = ctk.CTkComboBox(
            config_graficos,
            values=list(self.areas_norm.keys()),  # nomes das amostras
            width=300,
        )
        selecione_amostra.grid(column=0, row=0, padx=10, pady=10)

        # --- slider ---
        slider_valor = ctk.CTkSlider(config_graficos, from_=1, to=20, number_of_steps=19, width=200)
        slider_valor.set(5)
        slider_valor.grid(column=1, row=0, padx=10, pady=10, sticky="ew")

        label_slider = ctk.CTkLabel(config_graficos, text="Traço: 5%")
        label_slider.grid(column=2, row=0, padx=10, pady=10)

        # --- frame para gráficos ---
        frame_graficos = ctk.CTkFrame(config_graficos)
        frame_graficos.grid(column=0, row=1, columnspan=4, padx=10, pady=10, sticky="nsew")
        frame_graficos.grid_rowconfigure(0, weight=1)
        frame_graficos.grid_columnconfigure((0, 1), weight=1)

        canvas_maioritario = None
        canvas_traco = None

        # --- função de atualização dos gráficos ---
        def atualizar_graficos(*_):
            nonlocal canvas_maioritario, canvas_traco
            amostra_selecionada = selecione_amostra.get()
            if not amostra_selecionada:
                return

            # busca concentrações dessa amostra
            concs = None
            for dados in self.concentracoes.values():
                if amostra_selecionada in dados:
                    concs = dados[amostra_selecionada]
                    break
            if concs is None:
                return

            elementos = list(concs.keys())
            valores = [float(v) for v in concs.values()]

            # define limite de traço
            percentual = slider_valor.get()
            label_slider.configure(text=f"Traço: {percentual:.0f}%")
            soma_total = sum(valores)
            limite_traco = soma_total * (percentual / 100)

            # separa elementos
            elementos_traco, valores_traco = [], []
            elementos_majoritarios, valores_majoritarios = [], []
            soma_traco = 0

            for e, v in sorted(zip(elementos, valores), key=lambda x: x[1]):
                if soma_traco + v <= limite_traco:
                    elementos_traco.append(e)
                    valores_traco.append(v)
                    soma_traco += v
                else:
                    elementos_majoritarios.append(e)
                    valores_majoritarios.append(v)

            # --- gráfico majoritário ---
            if canvas_maioritario:
                canvas_maioritario.get_tk_widget().destroy()
            fig1, ax1 = plt.subplots(figsize=(4, 4))
            ax1.pie(
                valores_majoritarios + [soma_traco],
                labels=elementos_majoritarios + ["Traço"],
                autopct="%1.1f%%",
                startangle=140,
            )
            ax1.set_title(f"Gráfico Majoritário - {amostra_selecionada}")

            canvas_maioritario = FigureCanvasTkAgg(fig1, master=frame_graficos)
            canvas_maioritario.get_tk_widget().grid(row=0, column=0, sticky="nsew")
            plt.close(fig1)  # <<< FECHA a figura no matplotlib

            # --- gráfico traço ---
            if canvas_traco:
                canvas_traco.get_tk_widget().destroy()
            fig2, ax2 = plt.subplots(figsize=(4, 4))
            if valores_traco:
                ax2.pie(valores_traco, labels=elementos_traco, autopct="%1.1f%%", startangle=140)
            ax2.set_title(f"Gráfico Traço - até {percentual:.0f}%")

            canvas_traco = FigureCanvasTkAgg(fig2, master=frame_graficos)
            canvas_traco.get_tk_widget().grid(row=0, column=1, sticky="nsew")
            plt.close(fig2)  # <<< FECHA a figura no matplotlib

        # --- seleção do padrão (só quando houver mais de um) ---
        def trocar_padrao(rotulo):
            self.concentracoes = resultados_por_padrao[rotulo][0]
            atualizar_graficos()

        if len(rotulos) > 1:
            selecione_padrao = ctk.CTkComboBox(
                config_graficos, values=rotulos, width=220, state="readonly", command=trocar_padrao
            )
            selecione_padrao.set(rotulos[0])
            selecione_padrao.grid(column=3, row=0, padx=10, pady=10)

        # vincula eventos
        selecione_amostra.configure(command=lambda _: atualizar_graficos())
        slider_valor.configure(command=lambda _: atualizar_graficos())
