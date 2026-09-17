import { useState } from 'react';
import { CheckCircle2, CreditCard, ShieldCheck, X } from 'lucide-react';
import { createBillingOrder, verifyBillingPayment } from '../services/api';
import { ConfigResponse } from '../types';

interface UpgradeModalProps {
  isOpen: boolean;
  onClose: () => void;
  onActivated: () => Promise<void>;
  token: string;
  email: string;
  config: ConfigResponse | null;
}

function loadCheckoutScript(): Promise<void> {
  if ((window as any).Razorpay) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const existing = document.getElementById('razorpay-checkout-script');
    if (existing) {
      existing.addEventListener('load', () => resolve(), { once: true });
      existing.addEventListener('error', () => reject(new Error('Checkout could not be loaded.')), { once: true });
      return;
    }
    const script = document.createElement('script');
    script.id = 'razorpay-checkout-script';
    script.src = 'https://checkout.razorpay.com/v1/checkout.js';
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Checkout could not be loaded.'));
    document.body.appendChild(script);
  });
}

export function UpgradeModal({ isOpen, onClose, onActivated, token, email, config }: UpgradeModalProps) {
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activated, setActivated] = useState(false);

  if (!isOpen) return null;

  const currency = config?.paid_plan_currency || 'INR';
  const amount = (config?.paid_plan_amount_subunits || 49900) / 100;
  const price = new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(amount);
  const planDays = config?.paid_plan_duration_days || 30;

  const startCheckout = async () => {
    setError(null);
    setProcessing(true);
    try {
      await loadCheckoutScript();
      const order = await createBillingOrder(token);
      const Razorpay = (window as any).Razorpay;
      const checkout = new Razorpay({
        key: order.key_id,
        amount: order.amount,
        currency: order.currency,
        name: order.name,
        description: order.description,
        order_id: order.order_id,
        prefill: { email: order.customer_email || email },
        theme: { color: '#4f46e5' },
        handler: async (response: {
          razorpay_order_id: string;
          razorpay_payment_id: string;
          razorpay_signature: string;
        }) => {
          try {
            await verifyBillingPayment(response, token);
            await onActivated();
            setActivated(true);
          } catch (err: any) {
            setError(err.message || 'Payment verification is pending. Your payment has not been lost.');
          } finally {
            setProcessing(false);
          }
        },
        modal: {
          ondismiss: () => setProcessing(false),
        },
      });
      checkout.on('payment.failed', (response: any) => {
        setError(response?.error?.description || 'Payment failed. No plan change was made.');
        setProcessing(false);
      });
      checkout.open();
    } catch (err: any) {
      setError(err.message || 'Could not start checkout.');
      setProcessing(false);
    }
  };

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="upgrade-title">
      <div className="glass-card upgrade-modal">
        <button className="modal-close-btn" onClick={onClose} aria-label="Close upgrade dialog">
          <X size={20} />
        </button>

        {activated ? (
          <div className="upgrade-success">
            <CheckCircle2 size={48} />
            <h2 id="upgrade-title">Paid access is active</h2>
            <p>You now have unlimited translations for {planDays} days. Your history and persona remain unchanged.</p>
            <button className="btn btn-primary" onClick={onClose}>Continue to CrossSpeak AI</button>
          </div>
        ) : (
          <>
            <div className="upgrade-icon"><CreditCard size={24} /></div>
            <span className="badge badge-accent">Paid plan</span>
            <h2 id="upgrade-title">Unlimited CrossSpeak AI</h2>
            <p className="upgrade-price">{price} <span>/ {planDays} days</span></p>
            <ul className="upgrade-benefits">
              <li><CheckCircle2 size={17} /> Unlimited translations during the paid period</li>
              <li><CheckCircle2 size={17} /> Existing history and persona are preserved</li>
              <li><CheckCircle2 size={17} /> Fresh free allowance after paid access expires</li>
            </ul>

            {error && <div className="form-error">{error}</div>}

            {config?.payments_enabled ? (
              <button className="btn btn-primary upgrade-pay-btn" onClick={startCheckout} disabled={processing}>
                <ShieldCheck size={17} /> {processing ? 'Opening secure checkout…' : `Pay ${price} securely`}
              </button>
            ) : (
              <div className="checkout-unavailable">
                Checkout is being configured. Your free plan remains active and no payment can be taken yet.
              </div>
            )}
            <p className="upgrade-note">Payment is processed by Razorpay. Paid access starts only after server verification.</p>
          </>
        )}
      </div>
    </div>
  );
}
