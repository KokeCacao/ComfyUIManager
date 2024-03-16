class Foo {
  constructor() {
    this.bar = 1;
  }

  registerExtension() {
    console.log('registerExtension');
  }
}

export const app = new Foo();
