# GeminiProChat

English | [中文](README_cn.md) | [Italiano](README_it.md)

Minimal web UI for Gemini Pro Chat.
---

# Lucky10 桌面可视化工具

本仓库额外提供一个 Windows 桌面软件示例（`main.py`），用于“澳洲幸运10”数据可视化与“前五不定位·独胆”统计输出。

## 运行环境

- Windows 10/11
- Python 3.10+

## 快速启动

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## 数据格式

支持以下三种格式（空格/逗号皆可）：

1. `期号 + 10个数字`（范围 1–10）
2. `期号 + 10位数字串`（0–9 全排列，0 会映射为 10）
3. `仅 10个数字`（无期号）

## 打包（PyInstaller）

直接运行 `build.bat` 即可在 `dist/Lucky10Visualizer` 输出 onedir 版本：

```bash
build.bat
```

## 配置说明

`config.json` 里可配置默认数据文件、监控开关、去抖时间、显示期数等参数。

---


Live demo: [Gemini Pro Chat](https://www.geminiprochat.com)

[![image](https://github.com/babaohuang/GeminiProChat/assets/559171/d02fd440-401a-410d-a112-4b10935624c6)](https://www.geminiprochat.com)

## Deploy

### Deploy With Vercel(Recommended)

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/babaohuang/GeminiProChat&env=GEMINI_API_KEY&envDescription=Google%20API%20Key%20for%20GeminiProChat&envLink=https://makersuite.google.com/app/apikey&project-name=gemini-pro-chat&repository-name=gemini-pro-chat&demo-title=Gemini%20Pro%20Chat&demo-description=Minimal%20web%20UI%20for%20Gemini%20Pro.&demo-url=https%3A%2F%2Fgeminiprochat.com&demo-image=https%3A%2F%2Fgeminiprochat.com%2Ficon.svg)

Just click the button above and follow the instructions to deploy your own copy of the app.

> [!NOTE]
> #### Solution for "User location is not supported for the API use"
> If you encounter the issue **"User location is not supported for the API use"**, follow these steps to resolve it:
>
> 1. Go to this [**palm-netlify-proxy**](https://github.com/antergone/palm-netlify-proxy) repo and click **"Deploy With Netlify"**.
> 2. Once the deployment is complete, you will receive a domain name assigned by Netlify (e.g., `https://xxx.netlify.app`).
> 3. In your **Gemini Pro Chat** project, set an environment variable named `API_BASE_URL` with the value being the domain you got from deploying the palm proxy (`https://xxx.netlify.app`).
> 4. Redeploy your **Gemini Pro Chat** project to finalize the configuration. This should resolve the issue.
>
> Thanks to [**antergone**](https://github.com/antergone/palm-netlify-proxy) for providing this solution.

### Deploy on Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/v9QL5u?referralCode=tSzmIe)

Just click the button above and follow the instructions to deploy on Railway.

### Deploy on Zeabur

[![Deploy on Zeabur](https://zeabur.com/button.svg)](https://zeabur.com/templates/1103PJ)

Just click the button above and follow the instructions to deploy on Zeabur.

### Deploy With Docker

To deploy with Docker, you can use the following command:

```bash
docker run --name geminiprochat \
--restart always \
-p 3000:3000 \
-itd \
-e GEMINI_API_KEY=your_api_key_here \
babaohuang/geminiprochat:latest
```
Please make sure to replace `your_api_key_here` with your own GEMINI API key.

This will start the **geminiprochat** service, accessible at `http://localhost:3000`. 

## Environment Variables

You can control the website through environment variables.

| Name | Description | Required |
| --- | --- | --- |
| `GEMINI_API_KEY` | Your API Key for GEMINI. You can get it from [here](https://makersuite.google.com/app/apikey).| **✔** |
| `API_BASE_URL` | Custom base url for GEMINI API. Click [here](https://github.com/babaohuang/GeminiProChat?tab=readme-ov-file#solution-for-user-location-is-not-supported-for-the-api-use) to see when to use this. | ❌ |
| `HEAD_SCRIPTS` | Inject analytics or other scripts before `</head>` of the page | ❌ |
| `PUBLIC_SECRET_KEY` | Secret string for the project. Use for generating signatures for API calls | ❌ |
| `SITE_PASSWORD` | Set password for site, support multiple password separated by comma. If not set, site will be public | ❌ |

## Running Locally

### Pre environment
1. **Node**: Check that both your development environment and deployment environment are using `Node v18` or later. You can use [nvm](https://github.com/nvm-sh/nvm) to manage multiple `node` versions locally.

   ```bash
    node -v
   ```

2. **PNPM**: We recommend using [pnpm](https://pnpm.io/) to manage dependencies. If you have never installed pnpm, you can install it with the following command:

   ```bash
    npm i -g pnpm
   ```

3. **GEMINI_API_KEY**: Before running this application, you need to obtain the API key from Google. You can register the API key at [https://makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey).

### Getting Started

1. Install dependencies

   ```bash
    pnpm install
   ```

2. Copy the `.env.example` file, then rename it to `.env`, and add your [`GEMINI_API_KEY`](https://makersuite.google.com/app/apikey) to the `.env` file.

   ```bash
    GEMINI_API_KEY=AIzaSy...
   ```

3. Run the application, the local project runs on `http://localhost:3000/`.

   ```bash
    pnpm run dev
   ```

## V8 Analyzer CLI

This repository also contains a lightweight Python helper for analyzing v8 式号码走势。

- Entry point: `scripts/v8_analyzer.py`
- Input format: comma-separated numbers within **1–10** (latest issue at the end), e.g. `3,4,2,5,9,9,10,9,3,2`

Examples:

```bash
python scripts/v8_analyzer.py "3,4,2,5,9,9,10,9,3,2"
python scripts/v8_analyzer.py "1,10,1,10,1,10" --format table
```

The analyzer outputs segment labels, 3/5/10-period statistics (大小、奇偶节奏、012路分布、震荡率), the 小号/大号世界判定，以及最新一期的行为标签（延续/补缺/假段/断点）。

## Acknowledgements

This project is inspired by and based on the following open-source project:

- [ChatGPT-Demo](https://github.com/anse-app/chatgpt-demo) - For the foundational codebase and features.

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=babaohuang/geminiprochat&type=Timeline)](https://star-history.com/#babaohuang/geminiprochat&Timeline)

## Buy me a coffee

If this repo is helpful to you, buy me a coffee,thank you very much!😄

<a href="https://www.buymeacoffee.com/babaohuang" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174"></a>
