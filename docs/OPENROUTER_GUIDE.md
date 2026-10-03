# Guia de Configuração do OpenRouter no course2brain

O **course2brain** suporta nativamente o [OpenRouter.ai](https://openrouter.ai), permitindo que você utilize dezenas de modelos de inteligência artificial de última geração — incluindo **modelos 100% gratuitos** — com uma única chave de API unificada, mantendo total flexibilidade sem ficar preso a um único provedor.

---

## 🚀 Passo a Passo: Criando sua Conta e Chave de API

### 1. Criar Conta no OpenRouter
1. Acesse [openrouter.ai](https://openrouter.ai).
2. Clique em **Sign In** no canto superior direito.
3. Você pode se autenticar diretamente com sua conta Google, GitHub, MetaMask ou e-mail.

### 2. Gerar sua Chave de API
1. Após logar, acesse o menu de perfil ou vá diretamente para [openrouter.ai/keys](https://openrouter.ai/keys).
2. Clique no botão **Create Key**.
3. Escolha um nome para identificar a chave (ex: `course2brain`).
4. (Opcional) Você pode definir um limite de crédito se desejar, mas para modelos gratuitos não é necessário.
5. Clique em **Create** e copie a chave gerada (ela começa com `sk-or-v1-...`).
   > ⚠️ **Atenção:** Guarde a chave em um local seguro. Ela não será exibida novamente.

---

## ⚙️ Como Configurar no `course2brain`

Você tem duas formas simples de configurar a sua chave:

### Opção A: No arquivo `c2b.toml` (Recomendado)
No arquivo `c2b.toml` (na raiz do projeto ou em `~/.config/c2b/config.toml`):

```toml
[openrouter]
api_key = "sk-or-v1-sua-chave-aqui"
model = "google/gemma-4-31b-it:free"
rpm_limit = 15

# (Opcional) Defina o OpenRouter como provedor ativo padrão
[ai]
default_provider = "openrouter"
```

### Opção B: Via Variável de Ambiente
No seu terminal ou arquivo `.zshrc` / `.bashrc`:

```bash
export OPENROUTER_API_KEY="sk-or-v1-sua-chave-aqui"
export C2B_AI_PROVIDER="openrouter"
```

---

## 📊 Como Funcionam as Cotas Gratuitas no OpenRouter

Os modelos que possuem o sufixo `:free` no ID são **totalmente gratuitos** (custo de $0 por milhão de tokens de entrada e saída).

- **Limite de Taxa (RPM):** Modelos gratuitos possuem um teto padrão de **20 requisições por minuto (RPM)**. O `course2brain` possui um **Rate Limiter integrado** (`rpm_limit = 15`) que gerencia o fluxo automaticamente para nunca estourar esse limite.
- **Cota Diária para Contas sem Créditos:** Contas que nunca compraram créditos têm direito a **50 requisições gratuitas por dia**.
- **Cota Diária com Créditos Ativos:** Se você comprar pelo menos **$10 de crédito** na plataforma (que ficam na sua carteira e nunca expiram), o limite de modelos gratuitos sobe para **1.000 requisições por dia**.
- **Acompanhamento de Uso:** Você pode acompanhar seu consumo e limites em tempo real em [openrouter.ai/activity](https://openrouter.ai/activity).

---

## 🏆 Modelos Gratuitos Recomendados

Abaixo estão os melhores modelos gratuitos (`:free`) para utilizar com o `course2brain`:

| Modelo | Contexto | Custo | Melhor Uso no course2brain |
| :--- | :--- | :--- | :--- |
| **`google/gemma-4-31b-it:free`** ⭐ | **262k** tokens | **$0** | **Padrão recomendado para Síntese**: Modelo de 31B da Google DeepMind, excelente em Português (PT-BR), gera notas didáticas e ricas em Markdown. |
| **`qwen/qwen3.8-27b:free`** ⭐ | **262k** tokens | **$0** | **Padrão recomendado para Interlinks**: Modelo de 27B da Qwen, líder em precisão lógica e geração de JSON estrito. |
| **`nvidia/nemotron-3-ultra-550b-a55b:free`** | **1.000.000** tokens | **$0** | **Aulas Extensas / Maratonas**: Modelo MoE gigante da NVIDIA (550B total / 55B ativo). Janela colossal de 1 milhão de tokens para transcrições de várias horas. |
| **`nvidia/nemotron-3.5-lightning:free`** | **1.000.000** tokens | **$0** | **Baixa Latência**: Modelo rápido da NVIDIA com contexto de 1M, ideal para validações rápidas. |
| **`openrouter/free`** | **200k** tokens | **$0** | **Resiliência / Roteamento Dinâmico**: Roteador inteligente da OpenRouter que seleciona automaticamente o melhor modelo gratuito disponível. |

---

## 🎯 Configuração Granular por Tarefa (Avançado)

Você pode configurar provedores e modelos diferentes para a **Síntese de Aulas** e para o **Auto-Interlink**:

```toml
[openrouter]
api_key = "sk-or-v1-..."

[gemini]
api_key = "AIza..."

# Use Gemma 4 gratuito para resumir aulas e Qwen para validar interlinks
[ai.synthesis]
provider = "openrouter"
model = "google/gemma-4-31b-it:free"

[ai.interlink]
provider = "openrouter"
model = "qwen/qwen3.8-27b:free"
```

---

## 💎 Usando Modelos Pagos de Fronteira

Se desejar utilizar os modelos mais poderosos do mundo (como Claude 3.7 Sonnet da Anthropic ou GPT-4o da OpenAI), basta adicionar créditos na sua conta OpenRouter e especificar o identificador do modelo:

```toml
[ai.synthesis]
provider = "openrouter"
model = "anthropic/claude-3.7-sonnet"
```
