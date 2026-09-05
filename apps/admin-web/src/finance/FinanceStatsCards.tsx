import { Card,Statistic } from "antd";
import { money } from "./constants";

interface FinanceStatsCardsProps {
  summary: {
    amount_visible?: boolean;
    total_fee_amount?: number;
    pending?: number;
    approved?: number;
    paid_amount?: number;
    invoice_amount?: number;
    refund_amount?: number;
  };
}

export function FinanceStatsCards({ summary }: FinanceStatsCardsProps) {
  const amountVisible = summary.amount_visible !== false;

  return (
    <div className="finance-stats">
      <Card>
        <Statistic
          title="费用总额"
          value={amountVisible ? summary.total_fee_amount : "无权限"}
          formatter={(v) =>
            typeof v === "number" ? money(v) : String(v)
          }
        />
      </Card>
      <Card>
        <Statistic
          title="待审批"
          value={summary.pending}
          styles={{ content: { color: "#f39c12" } }}
        />
      </Card>
      <Card>
        <Statistic
          title="已审批"
          value={summary.approved}
          styles={{ content: { color: "#3c8dbc" } }}
        />
      </Card>
      <Card>
        <Statistic
          title="付款金额"
          value={amountVisible ? summary.paid_amount : "无权限"}
          formatter={(v) =>
            typeof v === "number" ? money(v) : String(v)
          }
          styles={{ content: { color: "#00a65a" } }}
        />
      </Card>
      <Card>
        <Statistic
          title="开票金额"
          value={amountVisible ? summary.invoice_amount : "无权限"}
          formatter={(v) =>
            typeof v === "number" ? money(v) : String(v)
          }
        />
      </Card>
      <Card>
        <Statistic
          title="退费金额"
          value={amountVisible ? summary.refund_amount : "无权限"}
          formatter={(v) =>
            typeof v === "number" ? money(v) : String(v)
          }
          styles={{ content: { color: "#dd4b39" } }}
        />
      </Card>
    </div>
  );
}

export default FinanceStatsCards;
