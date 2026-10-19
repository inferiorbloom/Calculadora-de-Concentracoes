import customtkinter as ctk
from PIL import Image
import json
from tkinter import messagebox
import winsound

from models.PadraoModel import padroes_semelhantes
from resource_utils import resource_path


class Gerenciar_PadraoView(ctk.CTkFrame):

    def __init__(self, sidebar, frame, dynamic_frame, variaveis, padrao_view):
        super().__init__(sidebar)

        self.variaveis = variaveis
        self.caminho_json = self.variaveis.path
        self.frame = frame
        self.dynamic_frame = dynamic_frame

        # combobox principal da tela anterior
        self.combo_principal = padrao_view

        icone_gear = ctk.CTkImage(
            light_image=Image.open(resource_path("imagens", "icones", "gear.png")),
            size=(20, 20)
        )

        self.botao_gerenciar = ctk.CTkButton(
            self.frame,
            text="",
            image=icone_gear,
            width=40,
            height=30,
            corner_radius=8,
            fg_color="#213A57",
            command=self.janela_gerenciar,
        )

        self.botao_gerenciar.pack(side="right", padx=(0, 20))

        # Elementos Al → U
        self.elementos = [
                "Al","Si","P","S","Cl","Ar","K","Ca","Sc","Ti","V","Cr","Mn",
                "Fe","Co","Ni","Cu","Zn","Ga","Ge","As","Se","Br","Kr","Rb","Sr",
                "Y","Zr","Nb","Mo","Tc","Ru","Rh","Pd","Ag","Cd","In","Sn","Sb",
                "Te","I","Xe","Cs","Ba","La","Ce","Pr","Nd","Pm","Sm","Eu","Gd",
                "Tb","Dy","Ho","Er","Tm","Yb","Lu","Hf","Ta","W","Re","Os","Ir",
                "Pt","Au","Hg","Tl","Pb","Bi","Po","At","Rn","Fr","Ra","Ac","Th",
                "Pa","U","Np","Pu"
        ]

    # -------------------------
    # JANELA
    # -------------------------

    def janela_gerenciar(self):

        # relê do disco: com várias abas de alvo abertas, a cópia em memória pode estar velha, e salvar
        # a partir dela apagaria o que foi editado em outra aba
        try:
            with open(self.caminho_json, "r", encoding="utf-8") as arquivo:
                self.padroes = json.load(arquivo)
            self.variaveis.padroes = self.padroes.copy()
        except (OSError, ValueError):
            self.padroes = list(self.variaveis.padroes or [])

        self.win = ctk.CTkToplevel()
        self.win.title("Gerenciar Padrões")
        self.win.geometry("1000x700")
        self.win.grab_set()

        largura, altura = 1000, 700
        x = (self.win.winfo_screenwidth() // 2) - (largura // 2)
        y = (self.win.winfo_screenheight() // 2) - (altura // 2)
        self.win.geometry(f"{largura}x{altura}+{x}+{y}")

        self.win.columnconfigure(0, weight=1)
        self.win.columnconfigure(1, weight=2)
        self.win.rowconfigure(0, weight=1)

        # -------------------------
        # LISTA DE PADRÕES
        # -------------------------

        frame_lista = ctk.CTkFrame(self.win)
        frame_lista.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        ctk.CTkLabel(
            frame_lista,
            text="Padrões",
            font=("Arial Black", 16)
        ).pack(pady=10)

        bot_add = ctk.CTkButton(
            frame_lista,
            text="+ Adicionar Novo Padrão",
            fg_color="#1f6aa5",
            command=self.adicionar_padrao
        )
        bot_add.pack(pady=(0, 10))

        nomes = [p["nome"] for p in self.padroes]

        self.frame_lista_padroes = ctk.CTkScrollableFrame(frame_lista)
        self.frame_lista_padroes.pack(fill="both", expand=True, padx=10, pady=10)

        self.botoes_padroes = {}
        self.padrao_selecionado = None

        # -------------------------
        # TABELA DE EDIÇÃO
        # -------------------------

        frame_form = ctk.CTkFrame(self.win)
        frame_form.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)



        frame_busca = ctk.CTkFrame(frame_form, fg_color="transparent")
        frame_busca.pack(pady=(0,10))

        ctk.CTkLabel(
            frame_busca,
            text="Buscar elemento:", font=("Arial Black", 16)
        ).pack(side="left", padx=(0,10),)

        self.entry_busca = ctk.CTkEntry(frame_busca, width=150)
        self.entry_busca.pack(side="left")

        self.entry_busca.bind("<KeyRelease>", self.autocomplete_elementos)

        self.lista_sugestoes = ctk.CTkFrame(frame_form, fg_color = "#6d6d6d")
        self.lista_sugestoes.pack(fill="x", padx=20, pady=(0,10))


        ctk.CTkLabel(
            frame_form,
            text="Editar Padrão",
            font=("Arial Black", 16)
        ).pack(pady=10)

        nome_frame = ctk.CTkFrame(frame_form, fg_color="transparent")
        nome_frame.pack(pady=10)

        ctk.CTkLabel(
            nome_frame,
            text="Nome do padrão"
        ).pack()

        linha_nome = ctk.CTkFrame(nome_frame, fg_color="transparent")
        linha_nome.pack(pady=5)

        self.entry_nome = ctk.CTkEntry(linha_nome, width=250)
        self.entry_nome.pack(side="left", padx=(0, 10))

        bot_salvar_nome = ctk.CTkButton(
            linha_nome,
            text="Salvar",
            width=80,
            fg_color="#00992e",
            command=self.salvar_padroes
        )
        bot_salvar_nome.pack(side="left")

        # -------------------------
        # TABELA
        # -------------------------

        self.scroll = ctk.CTkScrollableFrame(frame_form, height=500)
        self.scroll.pack(fill="both", expand=True, padx=20, pady=10)

        headers = ["Elemento", "Concentração", "Erro", "Unidade"]

        for col, h in enumerate(headers):
            ctk.CTkLabel(
                self.scroll,
                text=h,
                font=("Arial Black", 13)
            ).grid(row=0, column=col, padx=10, pady=10)

        self.entries = {}

        for row, elemento in enumerate(self.elementos, start=1):

            ctk.CTkLabel(self.scroll, text=elemento).grid(row=row, column=0)

            conc = ctk.CTkEntry(self.scroll, width=120)
            conc.grid(row=row, column=1)

            erro = ctk.CTkEntry(self.scroll, width=80)
            erro.grid(row=row, column=2)

            unidade = ctk.CTkComboBox(
                self.scroll,
                values=["mg/kg","g/kg"],
                width=80,
                state="readonly",  # só unidades que a Sensibilidade e os gráficos sabem converter
            )
            unidade.set("mg/kg")
            unidade.grid(row=row, column=3)

            self.entries[elemento] = {
                "valor": conc,
                "erro": erro,
                "unidade": unidade
            }


 

        # carregar primeiro padrão
        self.atualizar_lista_json()
        if nomes:
            self.selecionar_padrao_lista(nomes[0])

        bot_excluir = ctk.CTkButton(
            frame_lista,
            text="Excluir padrão",
            fg_color="#8B0000",
            command=self.excluir_padrao
        )

        bot_excluir.pack(pady=10)


    # -------------------------
    # ADICIONAR PADRÃO
    # -------------------------

    def adicionar_padrao(self):

        numero = len(self.padroes) + 1
        nome = f"Novo_Padrao_{numero}"

        novo = {
            "nome": nome,
            "elementos": {}
        }

        self.padroes.append(novo)

        nomes = [p["nome"] for p in self.padroes]

        self.atualizar_lista_json()
        self.selecionar_padrao_lista(nome)


    def selecionar_padrao_lista(self, nome):

        self.padrao_selecionado = nome

        # resetar cores
        for bot in self.botoes_padroes.values():
            bot.configure(fg_color="#2b2b2b")

        # destacar selecionado
        self.botoes_padroes[nome].configure(fg_color="#1f6aa5")

        # carregar no editor
        self.padrao_selecionado = nome
        self.carregar_padrao(nome)

    def autocomplete_elementos(self, event=None):

        termo = self.entry_busca.get().strip().lower()

        # limpa sugestões antigas
        for widget in self.lista_sugestoes.winfo_children():
            widget.destroy()

        if not termo:
            return

        sugestoes = [e for e in self.elementos if termo in e.lower()]

        for i, elemento in enumerate(sugestoes[:16]):

            bot = ctk.CTkButton(
                self.lista_sugestoes,
                text=elemento,
                width=35,
                height=25,
                command=lambda e=elemento: self.ir_para_elemento(e)
            )

            bot.grid(row=i//8, column=i%8, padx=5, pady=5)


    def ir_para_elemento(self, elemento):

        if elemento not in self.entries:
            return

        widget = self.entries[elemento]["valor"]

        # foco no campo
        widget.focus_set()
        widget.select_range(0, "end")

        # força atualização de layout
        self.scroll.update_idletasks()

        # posição do widget dentro do scroll
        y = widget.winfo_rooty() - self.scroll.winfo_rooty()

        # altura total da área
        altura = self.scroll.winfo_height()

        # fração para scroll
        fracao = y / altura

        # move o scroll
        self.scroll._parent_canvas.yview_moveto(fracao)

        # limpar busca
        self.entry_busca.delete(0, "end")

        for w in self.lista_sugestoes.winfo_children():
            w.destroy()
    
    # -------------------------
    # CARREGAR PADRÃO
    # -------------------------
    def carregar_padrao(self, nome):
        padrao = next((p for p in self.padroes if p["nome"] == nome), None)

        if not padrao:
            return

        self.entry_nome.delete(0, "end")
        self.entry_nome.insert(0, padrao["nome"])

        for elemento in self.elementos:
            campos = self.entries[elemento]

            # Limpa os campos antes de preencher
            campos["valor"].delete(0, "end")
            campos["erro"].delete(0, "end")
            
            # Valor padrão caso não exista no JSON
            campos["unidade"].set("mg/kg") 

            if elemento in padrao["elementos"]:
                dados = padrao["elementos"][elemento]

                # Recupera os valores numéricos ou strings
                valor_str = dados.get("valor_str")
                valor = dados.get("valor")
                erro_str = dados.get("erro_str")
                erro = dados.get("erro")
                
                # --- AQUI ESTA A CORREÇÃO PARA A UNIDADE ---
                unidade_salva = dados.get("unidade", "mg/kg")
                campos["unidade"].set(unidade_salva)
                # -------------------------------------------

                valor_final = valor_str if valor_str is not None else ("" if valor is None else str(valor))
                erro_final = erro_str if erro_str is not None else ("" if erro is None else str(erro))

                campos["valor"].insert(0, valor_final)
                campos["erro"].insert(0, erro_final)

    # -------------------------
    # LISTA VISUAL
    # -------------------------

    def atualizar_lista_json(self):

        for widget in self.frame_lista_padroes.winfo_children():
            widget.destroy()

        self.botoes_padroes = {}

        for padrao in self.padroes:

            nome = padrao["nome"]

            bot = ctk.CTkButton(
                self.frame_lista_padroes,
                text=nome,
                fg_color="#2b2b2b",
                anchor="w",
                command=lambda n=nome: self.selecionar_padrao_lista(n)
            )

            bot.pack(fill="x", pady=2)

            self.botoes_padroes[nome] = bot

    # -------------------------
    # SALVAR JSON
    # -------------------------

    @staticmethod
    def _ler_numero(texto, elemento, campo):
        """Aceita vírgula ou ponto decimal; devolve (número, texto normalizado com ponto)."""
        texto = (texto or "").strip().replace(",", ".")
        if not texto:
            return None, None
        try:
            numero = float(texto)
        except ValueError:
            raise ValueError(f"{elemento}: o {campo} \"{texto}\" não é um número.") from None
        if numero < 0:
            raise ValueError(f"{elemento}: o {campo} não pode ser negativo.")
        return numero, texto

    def _confirmar_se_parecido(self, padrao, nome_original):
        """
        Padrão novo (ou renomeado) parecido com um já cadastrado: pergunta antes de salvar, sem impedir
        (pode ser parecido mas diferente). Editar um padrão existente sem mudar o nome não pergunta.
        """
        ja_existia = any(p["nome"] == nome_original and p.get("elementos") for p in self.padroes)
        if ja_existia and padrao["nome"] == nome_original:
            return True
        outros = [p for p in self.padroes if p["nome"] != nome_original and p.get("elementos")]
        parecidos = padroes_semelhantes(padrao, outros)
        if not parecidos:
            return True
        lista = "\n".join(f"• {nome}\n   ({'; '.join(motivos)})" for nome, motivos in parecidos)
        return messagebox.askyesno(
            "Padrão parecido",
            f"Este padrão é parecido com {'outro já existente' if len(parecidos) == 1 else 'outros já existentes'}:"
            f"\n\n{lista}\n\nDeseja realmente salvar \"{padrao['nome']}\" como um novo padrão?",
            icon="warning",
            parent=getattr(self, "win", None),
        )

    def salvar_padroes(self):
        nome = self.padrao_selecionado or self.entry_nome.get().strip()
        novo_nome = self.entry_nome.get().strip() or nome
        if not novo_nome:
            messagebox.showerror("Erro", "Dê um nome ao padrão antes de salvar.")
            return
        if novo_nome != nome and any(p["nome"] == novo_nome for p in self.padroes):
            messagebox.showerror("Erro", f"Já existe um padrão chamado \"{novo_nome}\".")
            return

        # valida tudo antes de gravar, para não salvar um padrão pela metade
        dados_elementos = {}
        try:
            for elemento, campos in self.entries.items():
                valor, valor_str = self._ler_numero(campos["valor"].get(), elemento, "valor")
                if valor is None:
                    continue
                erro, erro_str = self._ler_numero(campos["erro"].get(), elemento, "erro")
                dados_elementos[elemento] = {
                    "valor": valor,
                    "valor_str": valor_str,
                    "erro": erro,
                    "erro_str": erro_str,
                    "unidade": campos["unidade"].get(),
                }
        except ValueError as e:
            messagebox.showerror("Erro", f"Não foi possível salvar:\n{e}")
            return

        padrao = {"nome": novo_nome, "elementos": dados_elementos}
        if not self._confirmar_se_parecido(padrao, nome):
            return
        existentes = [p for p in self.padroes if p["nome"] != nome]
        existentes.append(padrao)

        try:
            with open(self.caminho_json, "w", encoding="utf-8") as f:
                json.dump(existentes, f, indent=4, ensure_ascii=False)
        except OSError as e:
            messagebox.showerror("Erro", f"Falha ao gravar o arquivo de padrões:\n{e}")
            return

        self.variaveis.padroes = existentes.copy()
        self.padroes = existentes
        self.padrao_selecionado = padrao["nome"]
        self.atualizar_lista_json()

        if self.combo_principal:
            self.combo_principal.atualizar_lista(existentes)

        messagebox.showinfo("Sucesso", "Padrões atualizados!")

    def atualizar_lista_json(self):

        for widget in self.frame_lista_padroes.winfo_children():
            widget.destroy()

        self.botoes_padroes = {}

        for padrao in self.padroes:

            nome = padrao["nome"]

            bot = ctk.CTkButton(
                self.frame_lista_padroes,
                text=nome,
                fg_color="#2b2b2b",
                anchor="w",
                command=lambda n=nome: self.selecionar_padrao_lista(n)
            )

            bot.pack(fill="x", pady=2)

            self.botoes_padroes[nome] = bot

    def excluir_padrao(self):

        if not self.padrao_selecionado:
            messagebox.showwarning("Aviso", "Selecione um padrão primeiro")
            return
        
        winsound.MessageBeep()
        confirmar = messagebox.askyesno(
            "Excluir",
            f"Deseja excluir '{self.padrao_selecionado}'?"
        )

        if not confirmar:
            return

        self.padroes = [
            p for p in self.padroes
            if p["nome"] != self.padrao_selecionado
        ]
        # SALVAR AUTOMATICAMENTE
        with open(self.caminho_json, "w", encoding="utf-8") as f:
            json.dump(self.padroes, f, indent=4, ensure_ascii=False)

        self.variaveis.padroes = self.padroes.copy()

        self.padrao_selecionado = None

        nomes = [p["nome"] for p in self.padroes]
        self.padrao_selecionado = nomes[0] if nomes else None

        if self.padrao_selecionado:
            self.carregar_padrao(self.padrao_selecionado)

        self.atualizar_lista_json()
        
        if self.combo_principal:
            self.combo_principal.atualizar_lista(self.padroes)

