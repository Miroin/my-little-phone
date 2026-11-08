import type {CapacitorConfig} from '@capacitor/cli';

const config:CapacitorConfig={
  appId:'com.miroin.mylittlephone',
  appName:'沈砚的小手机',
  webDir:'dist',
  server:{androidScheme:'https'},
  ios:{contentInset:'always',preferredContentMode:'mobile'},
  android:{allowMixedContent:false},
};

export default config;
