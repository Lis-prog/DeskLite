import { PriorityBadge } from "@/components/PriorityBadge";
import { Spinner } from "@/components/Spinner";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { Avatar } from "@/components/Avatar";
import { Card, CardHeader, CardBody } from "@/components/ui/Card";

// brenda return(), pas StatusBadge-ve ekzistuese:
<PriorityBadge priority="low" />
<PriorityBadge priority="urgent" />
<Spinner />
<Avatar name="Paulina Delija" />
<EmptyState title="No tickets yet" description="Create your first ticket." />
<ErrorState message="Could not load tickets." onRetry={() => alert('retry')} />
<Card>
  <CardHeader><p>Card test</p></CardHeader>
  <CardBody><p>Content here</p></CardBody>
</Card>