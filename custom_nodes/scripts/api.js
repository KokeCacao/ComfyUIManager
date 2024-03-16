class ComfyApi extends EventTarget {
  #registered = new Set();

  constructor() {
    super();
    const location = window.location;
    this.api_host = location.host;
    this.api_base = location.pathname.split('/').slice(0, -1).join('/');
    this.initialClientId = sessionStorage.getItem('clientId');
  }

  apiURL(route) {
    return this.api_base + route;
  }
}

export const api = new ComfyApi();
