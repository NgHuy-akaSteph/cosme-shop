import { Result, Button } from 'antd';

interface ErrorResultProps {
  message?: string;
  onRetry?: () => void;
}

export default function ErrorResult({ message = 'Có lỗi xảy ra', onRetry }: ErrorResultProps) {
  return (
    <Result
      status="error"
      title="Lỗi"
      subTitle={message}
      extra={
        onRetry && (
          <Button type="primary" onClick={onRetry}>
            Thử lại
          </Button>
        )
      }
    />
  );
}
