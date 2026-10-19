import os
import requests
import folium
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("SPTRANS_TOKEN")
BASE_URL = "https://api.olhovivo.sptrans.com.br/v2.1"


def main():
    if not TOKEN:
        print("Token não encontrado no arquivo .env")
        return

    sessao = requests.Session()

    resposta = sessao.post(
        f"{BASE_URL}/Login/Autenticar",
        params={"token": TOKEN},
        timeout=30
    )
    resposta.raise_for_status()

    if resposta.text.strip().lower() != "true":
        print("Erro: confira o token da SPTrans.")
        return

    print("Autenticado com sucesso!")

    resposta = sessao.get(
        f"{BASE_URL}/Linha/Buscar",
        params={"termosBusca": "Lapa"},
        timeout=30
    )
    resposta.raise_for_status()

    linhas = resposta.json()
    linha_escolhida = None
    paradas = []
    onibus = []

    for linha in linhas:
        codigo = linha.get("cl")

        # Não usar a linha 2506 dos slides
        if not codigo or codigo == 2506:
            continue

        r_paradas = sessao.get(
            f"{BASE_URL}/Parada/BuscarParadasPorLinha",
            params={"codigoLinha": codigo},
            timeout=30
        )
        r_paradas.raise_for_status()

        r_onibus = sessao.get(
            f"{BASE_URL}/Posicao/Linha",
            params={"codigoLinha": codigo},
            timeout=30
        )
        r_onibus.raise_for_status()

        paradas_teste = [
            p for p in r_paradas.json()
            if p.get("py") is not None and p.get("px") is not None
        ]

        onibus_teste = [
            v for v in r_onibus.json().get("vs", [])
            if v.get("py") is not None and v.get("px") is not None
        ]

        if paradas_teste and onibus_teste:
            linha_escolhida = linha
            paradas = paradas_teste
            onibus = onibus_teste
            break

    if linha_escolhida is None:
        print("Não encontrei uma linha com paradas e ônibus disponíveis.")
        print("Tente executar novamente mais tarde.")
        return

    pontos = [[p["py"], p["px"]] for p in paradas]
    pontos += [[v["py"], v["px"]] for v in onibus]

    centro = [
        sum(p[0] for p in pontos) / len(pontos),
        sum(p[1] for p in pontos) / len(pontos)
    ]

    mapa = folium.Map(
    location=centro,
    zoom_start=13,
    tiles="https://tile.openstreetmap.de/{z}/{x}/{y}.png",
    attr="© OpenStreetMap contributors"
)

    # Paradas: marcadores azuis
    for parada in paradas:
        folium.Marker(
            [parada["py"], parada["px"]],
            popup=parada.get("np", "Parada de ônibus"),
            tooltip="Parada de ônibus",
            icon=folium.Icon(color="blue")
        ).add_to(mapa)

    # Ônibus em circulação: marcadores vermelhos
    for veiculo in onibus:
        folium.Marker(
            [veiculo["py"], veiculo["px"]],
            popup=f"Ônibus: {veiculo.get('p', 'Não identificado')}",
            tooltip="Ônibus em circulação",
            icon=folium.Icon(
                color="red",
                icon="bus",
                prefix="fa"
            )
        ).add_to(mapa)

    folium.LayerControl().add_to(mapa)
    mapa.fit_bounds(pontos)
    mapa.save("mapa_onibus.html")

    print("Mapa criado: mapa_onibus.html")
    print("Linha:", linha_escolhida.get("lt"))
    print("Código da linha:", linha_escolhida.get("cl"))
    print("Quantidade de paradas:", len(paradas))
    print("Ônibus encontrados:", len(onibus))


if __name__ == "__main__":
    main()
