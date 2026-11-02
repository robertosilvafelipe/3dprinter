from fastapi import APIRouter, Form, Request

from app.domain.models import Category, Product, ProductKind
from app.services import core
from app.web import go, money, render, to_int, uow

router = APIRouter(prefix="/produtos")


@router.get("")
def listar(request: Request, cat: int = 0, q: str = ""):
    with uow:
        cats = uow.categories.list()
        prods = uow.products.list(lambda p: (not cat or p.category_id == cat)
                                  and (not q or q.lower() in (p.name + p.sku).lower()))
        stock = {p.id: core.stock_of(uow, p.id) for p in prods}
    return render(request, "produtos/lista.html", produtos=prods, cats={c.id: c for c in cats},
                  cat=cat, q=q, stock=stock)


@router.get("/novo")
def novo(request: Request):
    with uow:
        cats = uow.categories.list()
    return render(request, "produtos/form.html", p=None, cats=cats, kinds=list(ProductKind))


@router.get("/{pid}")
def editar(request: Request, pid: int):
    with uow:
        p, cats = uow.products.get(pid), uow.categories.list()
        st = core.stock_of(uow, pid) if p else None
    if not p:
        return go("/produtos", err="Produto não encontrado")
    return render(request, "produtos/form.html", p=p, cats=cats, st=st, kinds=list(ProductKind))


@router.post("/salvar")
def salvar(pid: int = Form(0), sku: str = Form(...), name: str = Form(...),
           category_id: int = Form(...), price: str = Form(...), cost: str = Form("0"),
           description: str = Form(""), material: str = Form(""), color: str = Form(""),
           print_time_min: str = Form("0"), weight_g: str = Form("0"),
           dimensions: str = Form(""), stl_url: str = Form(""), image_url: str = Form(""),
           active: str = Form(""), initial_qty: str = Form("0"), min_qty: str = Form("0")):
    try:
        fields = dict(sku=sku.strip().upper(), name=name.strip(), category_id=category_id,
                      price=money(price), cost=money(cost), description=description,
                      material=material, color=color, print_time_min=to_int(print_time_min),
                      weight_g=to_int(weight_g), dimensions=dimensions, stl_url=stl_url,
                      image_url=image_url, active=bool(active) or not pid)
        if pid:
            with uow:
                p = uow.products.get(pid)
                if uow.products.first(lambda o: o.sku == fields["sku"] and o.id != pid):
                    raise core.BusinessError("SKU já usado por outro produto.")
                for k, v in fields.items():
                    setattr(p, k, v)
                uow.products.update(p)
                st = core.stock_of(uow, pid)
                st.min_quantity = to_int(min_qty)
                uow.stock.update(st)
            return go(f"/produtos/{pid}", msg="Produto atualizado")
        p = core.create_product(uow, Product(**fields), to_int(initial_qty), to_int(min_qty))
        return go("/produtos", msg=f"Produto {p.name} cadastrado")
    except (core.BusinessError, ValueError) as e:
        return go(f"/produtos/{pid}" if pid else "/produtos/novo", err=str(e))


@router.post("/categorias")
def nova_categoria(name: str = Form(...), kind: ProductKind = Form(...)):
    with uow:
        uow.categories.add(Category(name.strip(), kind))
    return go("/produtos/novo", msg=f"Categoria {name} criada")
