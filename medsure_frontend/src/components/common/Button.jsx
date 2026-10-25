import React from 'react';

export const Button = ({
  children,
  variant = 'primary',
  size = 'md',
  block = false,
  loading = false,
  disabled = false,
  icon: Icon = null,
  onClick,
  type = 'button',
  className = '',
  id,
  title,
}) => {
  const classes = [
    'btn',
    `btn-${variant}`,
    size === 'lg' ? 'btn-lg' : size === 'sm' ? 'btn-sm' : '',
    block ? 'btn-block' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <button
      id={id}
      type={type}
      className={classes}
      onClick={onClick}
      disabled={disabled || loading}
      title={title}
    >
      {loading ? (
        <span
          className="spinner"
          style={{ width: '16px', height: '16px', borderWidth: '2px', marginRight: '4px' }}
        />
      ) : Icon ? (
        <Icon size={size === 'lg' ? 20 : size === 'sm' ? 14 : 16} />
      ) : null}
      <span>{children}</span>
    </button>
  );
};
