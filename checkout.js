(() => {
  "use strict";
  const CART_KEY="purity_cart";
  const money=n=>"₹"+Math.round(n).toLocaleString("en-IN");
  const escapeHtml=value=>String(value??"").replace(/[&<>"']/g,ch=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
  let cart=[];
  try{cart=JSON.parse(localStorage.getItem(CART_KEY))||[]}catch(_){cart=[]}
  const empty=document.getElementById("emptyCart");
  const layout=document.getElementById("checkoutLayout");
  const form=document.getElementById("checkoutForm");
  const errorBox=document.getElementById("checkoutError");

  function renderSummary(){
    if(!cart.length){empty.hidden=false;layout.hidden=true;return}
    const subtotal=cart.reduce((sum,item)=>sum+(Number(item.price)||0)*(Number(item.qty)||0),0);
    const delivery=subtotal>=2500?0:99;
    document.getElementById("itemCount").textContent=`${cart.reduce((n,i)=>n+(Number(i.qty)||0),0)} item(s)`;
    document.getElementById("orderItems").innerHTML=cart.map(item=>`<div class="order-item"><span>${escapeHtml(item.name)}<small>Qty: ${Number(item.qty)||0}</small></span><strong>${money((Number(item.price)||0)*(Number(item.qty)||0))}</strong></div>`).join("");
    document.getElementById("subtotal").textContent=money(subtotal);
    document.getElementById("delivery").textContent=delivery?money(delivery):"Free";
    document.getElementById("total").textContent=money(subtotal+delivery);
  }
  renderSummary();

  form.addEventListener("submit",async event=>{
    event.preventDefault();errorBox.hidden=true;
    if(!cart.length){errorBox.textContent="Your cart is empty.";errorBox.hidden=false;return}
    const button=document.getElementById("placeOrderBtn");
    const payload=Object.fromEntries(new FormData(form).entries());payload.items=cart;
    button.disabled=true;button.textContent="Placing order…";
    try{
      const response=await fetch("/api/orders",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
      const data=await response.json();
      if(!response.ok)throw new Error(data.error||"Unable to place your order.");
      localStorage.removeItem(CART_KEY);layout.hidden=true;document.querySelector(".checkout-heading").hidden=true;
      document.getElementById("successPanel").hidden=false;
      document.getElementById("successMessage").textContent=data.payment_method==="cod"?"Your demo order is confirmed. Payment is due on delivery.":"Your demo order is recorded. No real payment was processed or charged.";
      document.getElementById("successDetails").innerHTML=`<strong>Order #${data.order_id}</strong><br>Total: ${money(data.total_amount)}<br>Payment: ${escapeHtml(data.payment_method.toUpperCase())}<br>Status: ${escapeHtml(data.payment_status)}`;
      window.scrollTo({top:0,behavior:"smooth"});
    }catch(error){
      errorBox.textContent=error.message||"Something went wrong. Please try again.";errorBox.hidden=false;
      button.disabled=false;button.innerHTML='Place demo order <span>→</span>';
    }
  });
})();