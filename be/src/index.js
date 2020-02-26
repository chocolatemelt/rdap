import "core-js/stable";
import "regenerator-runtime/runtime";
import Koa from 'koa';

const app = new Koa();

app.use(async ctx => { ctx.body = 'hi' });
app.listen(3030);
