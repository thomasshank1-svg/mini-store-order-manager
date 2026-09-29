let state = { products: [], orders: [] };
const cart = new Map(JSON.parse(localStorage.getItem("store-cart") || "[]"));

function saveCart() {
  localStorage.setItem("store-cart", JSON.stringify([...cart.entries()]));
}

function cartItems() {
  return [...cart.entries()].map(([sku, quantity]) => ({ sku, quantity }));
}

function productBySku(sku) {
  return state.products.find((product) => product.sku === sku);
}

function renderProducts() {
  $("#products").innerHTML = state.products.map((product) => `
    <article class="item product">
      <div>
        <span class="badge">${esc(product.category)}</span>
        <h3>${esc(product.name)}</h3>
        <p>${esc(product.description)}</p>
        <strong>${money(product.price_cents)}</strong>
      </div>
      <div class="actions">
        <span>${product.stock} in stock</span>
        <button data-add="${esc(product.sku)}" ${product.stock < 1 ? "disabled" : ""}>Add</button>
      </div>
    </article>
  `).join("");
  document.querySelectorAll("[data-add]").forEach((button) => {
    button.addEventListener("click", () => {
      const sku = button.dataset.add;
      const product = productBySku(sku);
      const next = (cart.get(sku) || 0) + 1;
      if (next > product.stock) return toast("No more stock is available for that product.");
      cart.set(sku, next);
      saveCart();
      renderCart();
    });
  });
}

function renderCart() {
  const items = cartItems().map((item) => ({ ...item, product: productBySku(item.sku) })).filter((item) => item.product);
  $("#cartCount").textContent = `${items.reduce((sum, item) => sum + item.quantity, 0)} items`;
  if (!items.length) {
    $("#cart").innerHTML = '<p class="muted">Cart is empty.</p>';
    return;
  }
  const total = items.reduce((sum, item) => sum + item.quantity * item.product.price_cents, 0);
  $("#cart").innerHTML = items.map((item) => `
    <div class="item compact">
      <div>
        <strong>${esc(item.product.name)}</strong>
        <span>${item.quantity} x ${money(item.product.price_cents)}</span>
      </div>
      <button data-remove="${esc(item.sku)}" title="Remove">x</button>
    </div>
  `).join("") + `<div class="stat"><span>Total</span><strong>${money(total)}</strong></div>`;
  document.querySelectorAll("[data-remove]").forEach((button) => {
    button.addEventListener("click", () => {
      cart.delete(button.dataset.remove);
      saveCart();
      renderCart();
    });
  });
}

function renderOrders() {
  $("#orderTotal").textContent = `${state.orders.length} orders`;
  $("#orders").innerHTML = state.orders.map((order) => `
    <tr>
      <td>#${order.id}</td>
      <td>${esc(order.customer)}<br><span class="muted">${esc(order.email)}</span></td>
      <td>${money(order.total_cents)}</td>
      <td>${order.item_count}</td>
      <td>
        <select data-status="${order.id}">
          ${["Paid", "Packed", "Sent", "Refunded"].map((status) => `<option ${status === order.status ? "selected" : ""}>${status}</option>`).join("")}
        </select>
      </td>
    </tr>
  `).join("") || '<tr><td colspan="5">No orders yet.</td></tr>';
  document.querySelectorAll("[data-status]").forEach((select) => {
    select.addEventListener("change", () => action(select, async () => {
      await api("/api/status", { id: Number(select.dataset.status), status: select.value });
      await refresh();
    }));
  });
}

async function refresh() {
  state = await api("/api/state");
  for (const [sku, quantity] of cart) {
    const product = productBySku(sku);
    if (!product || quantity > product.stock) cart.delete(sku);
  }
  saveCart();
  renderProducts();
  renderCart();
  renderOrders();
}

$("#checkout").addEventListener("submit", (event) => {
  event.preventDefault();
  action(event.submitter, async () => {
    const form = Object.fromEntries(new FormData(event.currentTarget));
    const result = await api("/api/orders", { ...form, items: cartItems() });
    cart.clear();
    saveCart();
    event.currentTarget.reset();
    await refresh();
    toast(`Order #${result.id} created for ${money(result.total_cents)}.`);
  });
});

refresh().catch((error) => toast(error.message));
