<template>
  <section class="busca-similar">
    <form @submit.prevent="buscar">
      <label>{{ $t("map.geocoding.similar.street") }}
        <input v-model.trim="nome" maxlength="200" class="form-control" required @input="reiniciar" />
      </label>
      <button class="btn btn-search" :disabled="!nome || ocupado">{{ $t("map.geocoding.btnText") }}</button>
    </form>
    <ol v-if="candidatos.length">
      <li v-for="c in candidatos" :key="c.id">
        <button type="button" class="candidato" :aria-pressed="selecionado === c" @click="escolher(c)">
          {{ c.nome }} <small v-if="candidatos.some(outro => outro !== c && outro.nome === c.nome)">(#{{ c.id }})</small>
        </button>
      </li>
    </ol>
    <form v-if="selecionado" @submit.prevent="localizar">
      <label>{{ $t("map.geocoding.similar.number") }}
        <input class="form-control" v-model.trim="numero" inputmode="decimal" pattern="[0-9]{1,9}([.,][0-9]{1,6})?" required @input="limparPonto" />
      </label>
      <label>{{ $t("map.geocoding.similar.year") }}
        <input class="form-control" v-model.trim="ano" inputmode="numeric" pattern="[0-9]{4}" maxlength="4" required @input="limparPonto" />
      </label>
      <button class="btn btn-search" :disabled="ocupado">{{ $t("map.geocoding.similar.locate") }}</button>
    </form>
    <p role="status" aria-live="polite">{{ mensagem }}</p>
  </section>
</template>

<script>
import ApiMap from "@/middleware/Map";
import { Feature } from "ol";
import { Point } from "ol/geom";
import { Vector as VectorLayer } from "ol/layer";
import { Vector as VectorSource } from "ol/source";
import { overlayGroupGeolocation } from "@/views/assets/js/map/overlayGroup";
import { placeStyleSearch1 } from "@/views/assets/js/map/Styles";

export default {
  data() {
    return { nome: "", numero: "", ano: "", candidatos: [], selecionado: null,
      mensagem: "", ocupado: false, versao: 0 };
  },
  beforeDestroy() {
    this.versao++;
  },
  methods: {
    limparPonto() {
      this.versao++;
      this.ocupado = false;
      this.mensagem = "";
      const camadas = overlayGroupGeolocation.getLayers();
      const anterior = camadas.getArray().find(c => c.get("name") === "pontosTcc");
      if (anterior) camadas.remove(anterior);
    },
    reiniciar() {
      this.limparPonto();
      this.candidatos = [];
      this.selecionado = null;
    },
    escolher(candidato) {
      this.limparPonto();
      this.selecionado = candidato;
    },
    async buscar() {
      this.reiniciar();
      const versao = this.versao;
      this.ocupado = true;
      this.mensagem = this.$t("map.geocoding.similar.searching");
      try {
        const { data } = await ApiMap.candidatos(this.nome);
        if (versao !== this.versao) return;
        this.candidatos = data;
        this.mensagem = this.$t(data.length ? "map.geocoding.similar.choose" : "map.geocoding.similar.none");
      } catch (_) {
        if (versao === this.versao) this.mensagem = this.$t("map.geocoding.similar.error");
      } finally {
        if (versao === this.versao) this.ocupado = false;
      }
    },
    async localizar() {
      this.limparPonto();
      const versao = this.versao;
      this.ocupado = true;
      this.mensagem = this.$t("map.geocoding.similar.searching");
      try {
        const { data } = await ApiMap.pontosCandidato(this.selecionado.id, this.numero.replace(",", "."), this.ano);
        if (versao !== this.versao) return;
        if (!data.length) {
          this.mensagem = this.$t("map.geocoding.similar.noPoint");
          return;
        }
        const source = new VectorSource({ features: data.map(coord => new Feature(new Point(coord))) });
        const camada = new VectorLayer({ source, style: placeStyleSearch1, zIndex: 999 });
        camada.set("name", "pontosTcc");
        overlayGroupGeolocation.getLayers().push(camada);
        this.$root.olmap.getView().fit(source.getExtent(), { maxZoom: 18, padding: [48, 48, 48, 48] });
        this.mensagem = this.$t(data.length === 1 ? "map.geocoding.similar.point" : "map.geocoding.similar.points");
      } catch (_) {
        if (versao === this.versao) this.mensagem = this.$t("map.geocoding.similar.error");
      } finally {
        if (versao === this.versao) this.ocupado = false;
      }
    },
  },
};
</script>

<style scoped>
form { display: flex; align-items: end; flex-wrap: wrap; gap: .5rem; }
label { flex: 1; min-width: 6rem; }
ol { padding-left: 1.5rem; margin: .75rem 0; }
li { list-style: decimal; }
.candidato { border: 0; background: transparent; color: #174c71; text-align: left; text-decoration: underline; }
.candidato[aria-pressed="true"] { color: #222; font-weight: bold; }
p { margin: .5rem 0 0; }
</style>
