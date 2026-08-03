import { ComponentFixture, TestBed } from '@angular/core/testing';
import { beforeEach, describe, expect, it } from 'vitest';

import { AjudaLink } from './ajuda-link';

describe('AjudaLink', () => {
  let fixture: ComponentFixture<AjudaLink>;

  beforeEach(() => {
    TestBed.configureTestingModule({ imports: [AjudaLink] });
    fixture = TestBed.createComponent(AjudaLink);
  });

  function ancora(): HTMLAnchorElement {
    return fixture.nativeElement.querySelector('a');
  }

  it('aponta para a rota autenticada do manual, na seção da tela', () => {
    fixture.componentRef.setInput('manual', 'responsaveis-de-area');
    fixture.componentRef.setInput('secao', 'a-tela-minhas-tarefas');
    fixture.detectChanges();

    expect(ancora().getAttribute('href')).toBe(
      '/ajuda/responsaveis-de-area/#a-tela-minhas-tarefas',
    );
  });

  it('sem seção, abre o manual na capa', () => {
    fixture.componentRef.setInput('manual', 'departamento-pessoal');
    fixture.detectChanges();

    expect(ancora().getAttribute('href')).toBe('/ajuda/departamento-pessoal/');
  });

  it('abre em aba nova sem dar acesso à janela de origem', () => {
    // `noopener` é o que impede a aba aberta de alcançar `window.opener`.
    fixture.componentRef.setInput('manual', 'grupos-templates-regras');
    fixture.detectChanges();

    expect(ancora().getAttribute('target')).toBe('_blank');
    expect(ancora().getAttribute('rel')).toContain('noopener');
  });

  it('avisa no rótulo acessível que o manual abre fora da tela', () => {
    fixture.componentRef.setInput('manual', 'departamento-pessoal');
    fixture.detectChanges();

    expect(ancora().getAttribute('aria-label')).toContain('aba nova');
  });
});
