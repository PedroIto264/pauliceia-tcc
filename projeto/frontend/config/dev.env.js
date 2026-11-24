"use strict";
const { merge } = require("webpack-merge");
const prodEnv = require("./prod.env");

module.exports = merge(prodEnv, {
  NODE_ENV: '"development"',
  // urlVGI: '"http://localhost:3001"',
  urlVGI: '"https://pauliceia-dev.unifesp.br/api/vgi"',
  // urlGeoserverPauliceia: '"http://localhost:9021/geoserver/pauliceia"',
  urlGeoserverPauliceia:
    '"https://pauliceia-dev.unifesp.br/geoserver/pauliceia"',
  urlGeoserveOther: '"https://pauliceia-dev.unifesp.br/geoserver/other"',
  urlGeocoding: process.env.TCC_GEOCODING === "1"
    ? '"/api/geocoding"'
    : '"https://pauliceia-dev.unifesp.br/api/geocoding"',
  buscaTcc: JSON.stringify(process.env.TCC_GEOCODING === "1"),
  keyCripto: '"keytest"',
});
